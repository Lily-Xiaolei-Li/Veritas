"""
验证 lookup_introduction 功能
"""
import sys
sys.path.insert(0, r"C:\Users\Barry Li (UoN)\clawd\projects\Agent-B-Research\backend")

from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(r"C:\Users\Barry Li (UoN)\clawd\projects\Agent-B-Research\backend\.env"))

# 测试几个 CHUNKS_ 开头的论文
test_paper_ids = [
    "CHUNKS_Andon_et_al_2014_The_legitimacy_of_new_assurance_providers_Making_the_cap_fit",
    "CHUNKS_Power_1996_Making_Things_Auditable",
    "CHUNKS_10.1007_978-3-031-76618-3_20",
]

from qdrant_client import QdrantClient

qdrant = QdrantClient(host='localhost', port=6333)

print("=" * 60)
print("验证 Priority 1 论文查找")
print("=" * 60)

for paper_id in test_paper_ids:
    clean_id = paper_id[7:] if paper_id.startswith('CHUNKS_') else paper_id
    
    print(f"\n📄 测试: {clean_id[:50]}...")
    
    # 在 vf_profiles 中查找
    result = qdrant.scroll(
        collection_name="vf_profiles",
        scroll_filter={
            "should": [
                {"key": "paper_id", "match": {"value": paper_id}},
                {"key": "clean_id", "match": {"value": clean_id}},
            ]
        },
        limit=1,
        with_payload=True
    )
    
    points, _ = result
    if points:
        payload = points[0].payload
        print(f"  ✅ vf_profiles 找到!")
        print(f"     meta.title: {payload.get('meta', {}).get('title', 'N/A')[:50]}")
        print(f"     chunks_folder: {payload.get('chunks_folder', 'N/A')}")
    else:
        print(f"  ❌ vf_profiles 未找到")
    
    # 在 academic_papers 中查找
    result = qdrant.scroll(
        collection_name="academic_papers",
        scroll_filter={
            "must": [
                {"key": "paper_name", "match": {"value": clean_id}},
                {"key": "section", "match": {"value": "introduction"}}
            ]
        },
        limit=1,
        with_payload=True
    )
    
    points, _ = result
    if points:
        payload = points[0].payload
        print(f"  ✅ academic_papers 找到 introduction!")
        print(f"     text preview: {payload.get('text', 'N/A')[:100]}...")
    else:
        print(f"  ⚠️ academic_papers 未找到 introduction (可能论文没有这个章节)")

print("\n" + "=" * 60)
print("✅ 验证完成!")
