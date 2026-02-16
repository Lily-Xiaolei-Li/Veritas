import requests
import json

BASE = "http://localhost:8001/api/v1/knowledge-source"

# Test with one of the 14 Elsevier DOIs
dois = [
    "10.1016/j.jaccpubpol.2026.107406",
    "10.1016/j.jbusres.2025.115376",
    "10.1016/j.jclepro.2022.134725",
]

# Try downloading one
print("=== Single Download Test ===")
r = requests.post(f"{BASE}/download", json={"doi": dois[0]})
print(f"Status: {r.status_code}")
print(json.dumps(r.json(), indent=2))

# Try batch
print("\n=== Batch Test (3 DOIs) ===")
doi_text = "\n".join(dois)
r2 = requests.post(f"{BASE}/batch", json={"dois": doi_text})
print(f"Status: {r2.status_code}")
print(json.dumps(r2.json(), indent=2))

# Check queue
print("\n=== Queue ===")
r3 = requests.get(f"{BASE}/queue")
print(f"Status: {r3.status_code}")
print(json.dumps(r3.json(), indent=2))
