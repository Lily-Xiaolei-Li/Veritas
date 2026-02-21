import asyncio
import json
from pathlib import Path
from app.services.proliferomaxima.ref_extractor import ReferenceExtractor
from app.services.proliferomaxima.ref_normalizer import ReferenceNormalizer
from app.services.proliferomaxima.paper_selector import find_paper_md_files

PAPERS = ["Singh_2025", "Xing_2023", "Yang_et_al_2024"]
LIB = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")

async def main():
    ext = ReferenceExtractor(LIB)
    norm = ReferenceNormalizer()
    file_map = find_paper_md_files(LIB, PAPERS)
    
    all_refs = {}
    
    for pid in PAPERS:
        f = file_map.get(pid)
        print(f"\n{'='*60}")
        print(f"Paper: {pid}")
        print(f"File: {f.name if f else 'NOT FOUND'}")
        
        if not f or not f.exists():
            print("  SKIPPED - file not found")
            continue
        
        raw = ext.extract_raw_reference_section(f)
        print(f"  Raw section: {len(raw)} chars")
        
        if not raw:
            print("  SKIPPED - no reference section")
            continue
        
        # Count regex refs for comparison
        regex_refs = ext.extract_from_file(f)
        print(f"  Regex extraction: {len(regex_refs)} refs")
        
        # AI normalize (all refs, no cap for testing)
        results = await norm.normalize_references(raw, source_paper=f.name, max_refs=100)
        print(f"  AI normalized: {len(results)} refs")
        
        corrupted = sum(1 for r in results if r.get("corrupted"))
        print(f"  Corrupted: {corrupted}")
        
        all_refs[pid] = results
        
        # Show first 3
        for i, r in enumerate(results[:3]):
            s = r.get("structured", {})
            ch = r.get("cite_how", {})
            print(f"  [{i+1}] {s.get('title', '')[:70]} ({s.get('year')})")
            print(f"      Intext: {ch.get('intext_first')} -> {ch.get('intext_subsequent')}")
        if len(results) > 3:
            print(f"  ... and {len(results)-3} more")
    
    # Cross-paper dedup check
    print(f"\n{'='*60}")
    print("CROSS-PAPER OVERLAP CHECK")
    
    def ref_key(r):
        s = r.get("structured", {})
        title = (s.get("title") or "").lower().strip()[:50]
        year = s.get("year")
        return (title, year)
    
    all_keys = {}
    for pid, refs in all_refs.items():
        for r in refs:
            k = ref_key(r)
            if k[0]:  # skip empty titles
                if k not in all_keys:
                    all_keys[k] = []
                all_keys[k].append(pid)
    
    overlaps = {k: v for k, v in all_keys.items() if len(v) > 1}
    print(f"Total unique refs across all papers: {len(all_keys)}")
    print(f"Overlapping refs (appear in 2+ papers): {len(overlaps)}")
    for k, papers in list(overlaps.items())[:10]:
        print(f"  '{k[0][:50]}' ({k[1]}) -> {papers}")

asyncio.run(main())
