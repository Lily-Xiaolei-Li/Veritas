import requests, json, time

BASE = "http://localhost:8001/api/v1/knowledge-source"

# Test with a known OA paper
print("=== Search for OA paper ===")
r = requests.get(f"{BASE}/search", params={"q": "sustainability assurance reporting MDPI"})
items = r.json().get("items", [])
for i in items[:3]:
    print(f"  [{i.get('year')}] {i.get('title','?')[:60]}")
    print(f"    DOI: {i.get('doi')} | OA: {i.get('is_open_access')}")

# Try downloading a known OA MDPI paper
print("\n=== Download OA paper (MDPI) ===")
r2 = requests.post(f"{BASE}/download", json={"doi": "10.3390/su13031309"})
print(f"Status: {r2.status_code}")
result = r2.json()
print(json.dumps(result, indent=2))

# Check queue status
time.sleep(2)
print("\n=== Queue after download ===")
r3 = requests.get(f"{BASE}/queue")
for item in r3.json().get("items", []):
    print(f"  [{item['status']}] {item['kind']} - {item.get('input',{}).get('doi','?')}")
    if item.get('result'):
        res = item['result']
        print(f"    source: {res.get('source')} | file: {res.get('file_path','')[:50]}")
