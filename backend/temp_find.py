from app.services.proliferomaxima.paper_selector import PaperSelector
sel = PaperSelector()

# Try keyword search first
results = sel.select(filters={"year_from": 2025, "year_to": 2025})
print(f"Total 2025 papers: {len(results)}")

# Filter for CSR-related
csr_papers = []
for r in results:
    title = (r.get("title") or "").lower()
    if any(kw in title for kw in ["corporate social", "csr", "social responsibility", "sustainability reporting", "sustainability disclosure"]):
        csr_papers.append(r)
        print(f"  {r['paper_id']} | {r['title'][:90]}")

print(f"\nCSR-related 2025 papers: {len(csr_papers)}")
