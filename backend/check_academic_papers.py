"""
检查 academic_papers 集合的实际 payload 结构
"""
import requests
import json

QDRANT_URL = "http://localhost:6333"

response = requests.post(
    f"{QDRANT_URL}/collections/academic_papers/points/scroll",
    json={
        "limit": 5,
        "with_payload": True,
        "with_vector": False
    }
)

if response.status_code == 200:
    points = response.json().get("result", {}).get("points", [])
    print("=" * 70)
    print("academic_papers Payload 结构")
    print("=" * 70)
    
    for i, p in enumerate(points, 1):
        print(f"\n--- Point {i} ---")
        payload = p.get("payload", {})
        print(f"Keys: {list(payload.keys())}")
        
        for key, value in payload.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"  {key}: {value[:100]}...")
            else:
                print(f"  {key}: {value}")
else:
    print(f"Error: {response.text}")
