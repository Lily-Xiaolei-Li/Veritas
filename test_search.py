import requests

r = requests.get('http://localhost:8001/api/v1/knowledge-source/search', params={'q': 'carbon audit assurance'})
print(f"Status: {r.status_code}")
data = r.json()
items = data.get('items', [])
print(f"Results: {len(items)}")
for i in items[:5]:
    title = i.get("title", "?")[:70]
    year = i.get("year", "?")
    doi = i.get("doi", "?")
    oa = i.get("is_open_access", "?")
    print(f"  [{year}] {title}")
    print(f"    DOI: {doi} | OA: {oa}")

print("\n--- Stats ---")
r2 = requests.get('http://localhost:8001/api/v1/knowledge-source/stats')
print(f"Status: {r2.status_code}")
print(r2.json())
