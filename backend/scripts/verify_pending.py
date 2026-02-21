"""Verify if pending items really don't exist in VF store"""
import json
from qdrant_client import QdrantClient

client = QdrantClient(host="localhost", port=6333)

# Sample pending items to verify
samples = [
    ("Xhindole", 2024),  # 10.1002_csr.70123.md
    ("Chiucchi", None),  # 10.1007_978-3-031-76618-3_20.md
    ("Costa", None),     # 10.1007_978-3-031-78247-3_23.md
    ("Aslam", 2025),     # 10.1016_j.cpa.2025.102818.md
]

print("Verifying pending items in VF store...\n")

# Get all VF profiles
profiles, _ = client.scroll("vf_profiles", limit=2000, with_payload=True)

for author_name, year in samples:
    print(f"Searching: {author_name} ({year})")
    found = []
    
    for p in profiles:
        meta = p.payload.get("meta", {})
        authors = meta.get("authors", [])
        p_year = meta.get("year")
        
        # Check if author name appears in any author
        for a in authors:
            if author_name.lower() in a.lower():
                found.append({
                    "paper_id": p.payload.get("paper_id"),
                    "authors": authors[:2],
                    "year": p_year,
                    "title": meta.get("title", "")[:60]
                })
                break
    
    if found:
        print(f"  FOUND {len(found)} matches:")
        for f in found[:3]:
            print(f"    - {f['paper_id']}: {f['authors']} ({f['year']})")
            print(f"      {f['title']}...")
    else:
        print(f"  NOT FOUND in VF store")
    print()
