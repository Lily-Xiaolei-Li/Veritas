"""
End-to-end Proliferomaxima test:
1. AI-normalize refs from 3 papers
2. Filter to journal_article + book + book_chapter only
3. Deduplicate across papers
4. Resolve metadata via CrossRef/Semantic Scholar
5. Generate VF profiles for new refs
"""
import asyncio
import json
import sys
import logging
from pathlib import Path
from collections import Counter

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(message)s")
logger = logging.getLogger("prolif_e2e")

from app.services.proliferomaxima.ref_extractor import ReferenceExtractor
from app.services.proliferomaxima.ref_normalizer import ReferenceNormalizer
from app.services.proliferomaxima.api_resolver import ProliferomaximaAPIResolver
from app.services.proliferomaxima.dedup import ProliferomaximaDedup
import httpx

PAPERS = ["O_Dwyer_2011", "Boiral_2019", "Chen_2020"]
LIB = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")
ACADEMIC_TYPES = {"journal_article", "book", "book_chapter"}
SCANNED_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\Agent-B-Research\backend\data\proliferomaxima_scanned.json")
VF_API = "http://localhost:8001"
GATEWAY = "http://localhost:18789"
TOKEN = "cf8bf99bedae98b1c3feea260670dcb023a0dfb04fddf379"

from app.services.proliferomaxima.paper_selector import find_paper_md_files

async def generate_vf_profile(paper_id, metadata, abstract):
    """Generate VF profile via backend API"""
    payload = {
        "paper_id": paper_id,
        "metadata": metadata,
        "abstract": abstract,
        "full_text": None,
        "in_library": False,
        "agent": "helper",
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(f"{VF_API}/api/v1/vf/generate", json=payload)
        return r.status_code in (200, 201)

def build_paper_id(meta):
    import hashlib
    doi = str(meta.get("doi") or "").strip().lower()
    if doi:
        safe = "".join(c if c.isalnum() else "_" for c in doi)
        return f"doi_{safe[:120]}"
    title = str(meta.get("title") or "untitled").lower().strip()
    year = str(meta.get("year") or "0000")
    digest = hashlib.sha1(f"{title}|{year}".encode()).hexdigest()[:12]
    base = "_".join(title.split()[:6])
    base = "".join(c if c.isalnum() or c == "_" else "_" for c in base).strip("_") or "untitled"
    return f"ref_{year}_{base[:60]}_{digest}"

async def main():
    ext = ReferenceExtractor(LIB)
    norm = ReferenceNormalizer()
    resolver = ProliferomaximaAPIResolver()
    dedup = ProliferomaximaDedup(SCANNED_PATH)
    file_map = find_paper_md_files(LIB, PAPERS)
    
    # Step 1: AI normalize all refs
    all_normalized = []
    for paper_id in PAPERS:
        f = file_map.get(paper_id)
        if not f or not f.exists():
            logger.info(f"SKIP {paper_id} - no .md file")
            continue
        raw = ext.extract_raw_reference_section(f)
        if not raw:
            logger.info(f"SKIP {paper_id} - no reference section")
            continue
        logger.info(f"Normalizing {paper_id} ({len(raw)} chars)...")
        results = await norm.normalize_references(raw, source_paper=f.name, max_refs=150)
        logger.info(f"  {paper_id}: {len(results)} refs normalized")
        for r in results:
            r["_source_paper_id"] = paper_id
        all_normalized.extend(results)
    
    logger.info(f"\nTotal normalized: {len(all_normalized)}")
    
    # Step 2: Filter to academic types
    academic = [r for r in all_normalized if r.get("structured", {}).get("type", "other") in ACADEMIC_TYPES]
    logger.info(f"Academic only (journal_article + book + book_chapter): {len(academic)}")
    
    type_dist = Counter(r.get("structured", {}).get("type") for r in all_normalized)
    logger.info(f"Type distribution: {dict(type_dist)}")
    
    # Step 3: Deduplicate across papers
    seen_keys = set()
    unique_refs = []
    for r in academic:
        s = r.get("structured", {})
        # Key: normalized title + year
        title_norm = "".join(c for c in (s.get("title") or "").lower() if c.isalnum() or c == " ")[:50].strip()
        year = s.get("year")
        key = (title_norm, year)
        if key in seen_keys or not title_norm:
            continue
        seen_keys.add(key)
        unique_refs.append(r)
    
    logger.info(f"After cross-paper dedup: {len(unique_refs)} unique academic refs")
    
    # Step 4: Check against existing VF store
    new_refs = []
    existing_count = 0
    scanned_count = 0
    for r in unique_refs:
        s = r.get("structured", {})
        ref_dict = {
            "title": s.get("title", ""),
            "authors": s.get("authors", []),
            "year": s.get("year"),
            "doi": s.get("doi"),
        }
        if dedup.is_scanned(ref_dict):
            scanned_count += 1
            continue
        if dedup.existing_profile(ref_dict):
            existing_count += 1
            continue
        new_refs.append(r)
    
    logger.info(f"Already scanned: {scanned_count}")
    logger.info(f"Already in VF store: {existing_count}")
    logger.info(f"NEW refs to process: {len(new_refs)}")
    
    # Step 5: Resolve + generate VF profiles
    added = 0
    skipped_no_abstract = 0
    failed = 0
    processed_for_scan = []
    
    for i, r in enumerate(new_refs):
        s = r.get("structured", {})
        ref_dict = {
            "title": s.get("title", ""),
            "authors": s.get("authors", []),
            "year": s.get("year"),
            "doi": s.get("doi"),
            "journal": s.get("journal"),
        }
        
        logger.info(f"[{i+1}/{len(new_refs)}] Resolving: {s.get('title', '')[:60]} ({s.get('year')})")
        
        resolved = await resolver.resolve(ref_dict)
        abstract = str((resolved or {}).get("abstract") or "").strip()
        
        if not abstract:
            skipped_no_abstract += 1
            processed_for_scan.append(ref_dict)
            logger.info(f"  -> No abstract found, skipping")
            continue
        
        metadata = {
            "title": (resolved or {}).get("title") or s.get("title"),
            "authors": (resolved or {}).get("authors") or s.get("authors", []),
            "year": (resolved or {}).get("year") or s.get("year"),
            "doi": ((resolved or {}).get("doi") or s.get("doi") or "").lower() or None,
            "journal": (resolved or {}).get("journal") or s.get("journal"),
            "full_article": False,
            "confidence": "inferred",
            "source_spell": "proliferomaxima",
            "inferred_from": "abstract",
            "ref_type": s.get("type", "other"),
            "cite_how": r.get("cite_how", {}),
            "cited_by": [r.get("_source_paper_id")],
        }
        
        paper_id = build_paper_id(metadata)
        logger.info(f"  -> Generating VF profile: {paper_id}")
        
        ok = await generate_vf_profile(paper_id, metadata, abstract)
        processed_for_scan.append(ref_dict)
        
        if ok:
            added += 1
            logger.info(f"  -> SUCCESS")
        else:
            failed += 1
            logger.info(f"  -> FAILED")
    
    # Mark all processed as scanned
    dedup.mark_scanned(processed_for_scan)
    dedup.save_scanned()
    
    # Final summary
    print(f"\n{'='*60}", flush=True)
    print(f"PROLIFEROMAXIMA E2E TEST COMPLETE", flush=True)
    print(f"{'='*60}", flush=True)
    print(f"Source papers: {len(PAPERS)}", flush=True)
    print(f"Total refs normalized: {len(all_normalized)}", flush=True)
    print(f"Academic refs (journal+book+chapter): {len(academic)}", flush=True)
    print(f"Unique after dedup: {len(unique_refs)}", flush=True)
    print(f"Already in VF store: {existing_count}", flush=True)
    print(f"Already scanned: {scanned_count}", flush=True)
    print(f"New refs processed: {len(new_refs)}", flush=True)
    print(f"  Added to VF store: {added}", flush=True)
    print(f"  Skipped (no abstract): {skipped_no_abstract}", flush=True)
    print(f"  Failed: {failed}", flush=True)
    print(f"{'='*60}", flush=True)

asyncio.run(main())
