"""
检查 Qdrant 中实际存在的 paper_id 格式
"""
import requests

QDRANT_URL = "http://localhost:6333"

def get_sample_points(collection, limit=20):
    """获取集合中的样本数据"""
    response = requests.post(
        f"{QDRANT_URL}/collections/{collection}/points/scroll",
        json={
            "limit": limit,
            "with_payload": True,
            "with_vector": False
        }
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}

print("=" * 70)
print("Qdrant 数据样本检查")
print("=" * 70)

# 检查 vf_profiles
print("\n[vf_profiles collection]")
result = get_sample_points("vf_profiles", 10)
if "error" not in result:
    points = result.get("result", {}).get("points", [])
    print(f"样本 paper_ids:")
    paper_ids = set()
    for p in points:
        payload = p.get("payload", {})
        pid = payload.get("paper_id", "N/A")
        paper_ids.add(pid)
    for pid in list(paper_ids)[:10]:
        print(f"  - {pid}")
else:
    print(f"Error: {result['error']}")

# 检查 academic_papers
print("\n[academic_papers collection]")
result = get_sample_points("academic_papers", 30)
if "error" not in result:
    points = result.get("result", {}).get("points", [])
    print(f"样本 paper_ids:")
    paper_ids = set()
    for p in points:
        payload = p.get("payload", {})
        pid = payload.get("paper_id", "N/A")
        paper_ids.add(pid)
    for pid in sorted(list(paper_ids))[:15]:
        print(f"  - {pid}")
    
    print(f"\n共找到 {len(paper_ids)} 个不同的 paper_id")
else:
    print(f"Error: {result['error']}")

# 搜索特定前缀
print("\n[搜索 Ahrens 相关]")
response = requests.post(
    f"{QDRANT_URL}/collections/academic_papers/points/scroll",
    json={
        "filter": {
            "must": [
                {
                    "key": "paper_id",
                    "match": {"text": "Ahrens"}
                }
            ]
        },
        "limit": 10,
        "with_payload": True,
        "with_vector": False
    }
)
if response.status_code == 200:
    points = response.json().get("result", {}).get("points", [])
    if points:
        for p in points[:5]:
            print(f"  - {p.get('payload', {}).get('paper_id')}")
    else:
        print("  未找到匹配")
