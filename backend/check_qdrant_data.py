"""
检查 Qdrant 中论文的实际数据结构
"""
import requests
import json

QDRANT_URL = "http://localhost:6333"

def search_paper_in_qdrant(paper_id, collection="vf_profiles"):
    """搜索论文在 Qdrant 中的记录"""
    
    # 使用 scroll 搜索
    response = requests.post(
        f"{QDRANT_URL}/collections/{collection}/points/scroll",
        json={
            "filter": {
                "must": [
                    {
                        "key": "paper_id",
                        "match": {"value": paper_id}
                    }
                ]
            },
            "limit": 10,
            "with_payload": True,
            "with_vector": False
        }
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}

def search_chunks_in_qdrant(paper_id, collection="academic_papers"):
    """搜索论文在 academic_papers 中的 chunks"""
    
    response = requests.post(
        f"{QDRANT_URL}/collections/{collection}/points/scroll",
        json={
            "filter": {
                "must": [
                    {
                        "key": "paper_id",
                        "match": {"value": paper_id}
                    }
                ]
            },
            "limit": 20,
            "with_payload": True,
            "with_vector": False
        }
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}

# 测试论文
test_papers = [
    "Ahrens_Chapman_2006",
    "DeVilliers_et_al_2025",
]

print("=" * 70)
print("检查 Qdrant 中的论文数据")
print("=" * 70)

for pid in test_papers:
    print(f"\n📄 {pid}")
    print("-" * 50)
    
    # 检查 vf_profiles
    print("\n[vf_profiles collection]")
    result = search_paper_in_qdrant(pid, "vf_profiles")
    if "error" not in result:
        points = result.get("result", {}).get("points", [])
        print(f"  找到 {len(points)} 条记录")
        if points:
            payload = points[0].get("payload", {})
            print(f"  Payload keys: {list(payload.keys())}")
            if "title" in payload:
                print(f"  Title: {payload['title'][:60]}...")
            if "section_type" in payload:
                print(f"  Section type: {payload['section_type']}")
    else:
        print(f"  Error: {result['error']}")
    
    # 检查 academic_papers (chunks)
    print("\n[academic_papers collection]")
    result = search_chunks_in_qdrant(pid, "academic_papers")
    if "error" not in result:
        points = result.get("result", {}).get("points", [])
        print(f"  找到 {len(points)} chunks")
        if points:
            # 统计 section types
            sections = {}
            for p in points:
                st = p.get("payload", {}).get("section_type", "unknown")
                sections[st] = sections.get(st, 0) + 1
            print(f"  Section 分布: {sections}")
            
            # 显示第一个 chunk
            first = points[0].get("payload", {})
            print(f"  First chunk keys: {list(first.keys())}")
            if "text" in first:
                print(f"  Text preview: {first['text'][:100]}...")
    else:
        print(f"  Error: {result['error']}")

print("\n" + "=" * 70)
print("分析结论")
print("=" * 70)
