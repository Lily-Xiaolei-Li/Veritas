import asyncio
import json
import logging
import sys
from pathlib import Path
from app.services.proliferomaxima.ref_extractor import ReferenceExtractor
from app.services.proliferomaxima.ref_normalizer import ReferenceNormalizer
from app.services.proliferomaxima.paper_selector import find_paper_md_files

# Enable logging to see progress
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s %(name)s %(message)s")

PAPERS = ["O_Dwyer_2011", "Boiral_2019", "Chen_2020"]
LIB = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")

async def main():
    ext = ReferenceExtractor(LIB)
    norm = ReferenceNormalizer()
    file_map = find_paper_md_files(LIB, PAPERS)
    
    all_refs = {}
    
    for paper_id in PAPERS:
        f = file_map.get(paper_id)
        print(f"\n{'='*60}", flush=True)
        print(f"Paper: {paper_id}", flush=True)
        if not f or not f.exists():
            print("  SKIPPED - not found", flush=True)
            continue
        print(f"File: {f.name}", flush=True)
        
        raw = ext.extract_raw_reference_section(f)
        print(f"  Raw section: {len(raw)} chars", flush=True)
        
        if not raw:
            print("  SKIPPED - no reference section", flush=True)
            continue
        
        regex_refs = ext.extract_from_file(f)
        print(f"  Regex extraction: {len(regex_refs)} refs", flush=True)
        
        results = await norm.normalize_references(raw, source_paper=f.name, max_refs=150)
        print(f"  AI normalized: {len(results)} refs", flush=True)
        
        corrupted = sum(1 for r in results if r.get("corrupted"))
        print(f"  Corrupted: {corrupted}", flush=True)
        
        all_refs[paper_id] = results
        
        for i, r in enumerate(results[:3]):
            s = r.get("structured", {})
            ch = r.get("cite_how", {})
            title = s.get("title", "")[:60]
            print(f"  [{i+1}] {title} ({s.get('year')})", flush=True)
            print(f"      First: {ch.get('intext_first')} | After: {ch.get('intext_subsequent')}", flush=True)
        if len(results) > 3:
            print(f"  ... and {len(results)-3} more", flush=True)
    
    # Cross-paper overlap
    print(f"\n{'='*60}", flush=True)
    print("CROSS-PAPER OVERLAP ANALYSIS", flush=True)
    
    def ref_key(r):
        s = r.get("structured", {})
        title = "".join(c for c in (s.get("title") or "").lower() if c.isalnum() or c == " ")[:40].strip()
        year = s.get("year")
        return (title, year)
    
    all_keys = {}
    for paper_id, refs in all_refs.items():
        for r in refs:
            k = ref_key(r)
            if k[0]:
                if k not in all_keys:
                    all_keys[k] = set()
                all_keys[k].add(paper_id)
    
    total_unique = len(all_keys)
    overlaps = {k: v for k, v in all_keys.items() if len(v) > 1}
    three_way = {k: v for k, v in overlaps.items() if len(v) == 3}
    
    total_all = sum(len(refs) for refs in all_refs.values())
    print(f"Total refs across papers: {total_all}", flush=True)
    print(f"Unique refs (deduplicated): {total_unique}", flush=True)
    print(f"Overlapping (in 2+ papers): {len(overlaps)}", flush=True)
    print(f"In all 3 papers: {len(three_way)}", flush=True)
    print(f"Dedup savings: {total_all - total_unique} refs", flush=True)
    
    if overlaps:
        print(f"\nSample overlaps:", flush=True)
        for k, papers in list(overlaps.items())[:15]:
            print(f"  '{k[0][:50]}' ({k[1]}) -> {sorted(papers)}", flush=True)

asyncio.run(main())
