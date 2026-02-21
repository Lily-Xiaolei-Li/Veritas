from pathlib import Path
from app.services.proliferomaxima.paper_selector import PaperSelector, find_paper_md_files
from app.services.proliferomaxima.ref_extractor import ReferenceExtractor

sel = PaperSelector()
lib = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")
ext = ReferenceExtractor(lib)

# Get all papers, find ones with .md AND reference sections, CSR-related
all_papers = sel.select(filters={})
pids = [r["paper_id"] for r in all_papers]
fmap = find_paper_md_files(lib, pids)

# Build title lookup
title_map = {r["paper_id"]: r for r in all_papers}

candidates = []
for pid, f in fmap.items():
    if not f or not f.exists():
        continue
    title = (title_map.get(pid, {}).get("title") or "").lower()
    if not any(kw in title for kw in ["social", "sustainab", "csr", "environment", "disclosure", "carbon", "audit"]):
        continue
    raw = ext.extract_raw_reference_section(f)
    if len(raw) > 500:
        regex_count = len(ext.extract_from_file(f))
        year = title_map.get(pid, {}).get("year")
        candidates.append((pid, year, regex_count, len(raw), title[:80]))

candidates.sort(key=lambda x: -x[2])  # sort by ref count desc
print(f"CSR papers with reference sections: {len(candidates)}")
for pid, year, rc, raw_len, title in candidates[:15]:
    print(f"  {pid} ({year}) | {rc} regex refs | {raw_len} chars | {title}")
