import asyncio
from pathlib import Path
from collections import Counter
from app.services.proliferomaxima.ref_extractor import ReferenceExtractor
from app.services.proliferomaxima.ref_normalizer import ReferenceNormalizer
from app.services.proliferomaxima.paper_selector import find_paper_md_files

PAPERS = ["O_Dwyer_2011", "Boiral_2019", "Chen_2020"]
LIB = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")

async def main():
    ext = ReferenceExtractor(LIB)
    norm = ReferenceNormalizer()
    file_map = find_paper_md_files(LIB, PAPERS)
    
    # Just do first paper (O'Dwyer) to check types - save time
    f = file_map.get("O_Dwyer_2011")
    raw = ext.extract_raw_reference_section(f)
    results = await norm.normalize_references(raw, source_paper=f.name, max_refs=150)
    
    print(f"O'Dwyer 2011: {len(results)} refs")
    types = Counter()
    for r in results:
        t = r.get("structured", {}).get("type", "unknown")
        types[t] += 1
    
    print("\nType distribution:")
    for t, c in types.most_common():
        print(f"  {t}: {c}")
    
    print("\nSample non-journal refs:")
    for r in results:
        s = r.get("structured", {})
        t = s.get("type", "")
        if t != "journal_article":
            title = s.get("title", "")[:70]
            authors = ", ".join((s.get("authors") or [])[:2])
            print(f"  [{t}] {authors} - {title} ({s.get('year')})")

asyncio.run(main())
