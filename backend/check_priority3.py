"""
详细检查 Priority 3: 在 Qdrant 但无 chunks 文件夹的论文
"""
import sqlite3
import requests
from pathlib import Path

QDRANT_URL = "http://localhost:6333"
chunks_dir = Path(r'C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks')

conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print("=" * 70)
print("Priority 3 详细分析: 在 Qdrant 但无 chunks 文件夹")
print("=" * 70)

# 获取这类论文
cur.execute("""
SELECT paper_id, title, vf_profile_exists, vf_chunks_generated, 
       has_abstract, has_introduction, has_methodology, has_conclusion
FROM papers 
WHERE in_vf_store = 1 
AND (has_chunks_folder = 0 OR has_chunks_folder IS NULL)
LIMIT 20
""")

papers = cur.fetchall()
print(f"\n找到样本: {len(papers)} 篇")

print("\n" + "-" * 70)
print("SQLite 记录的 VF chunks 信息:")
print("-" * 70)

for p in papers[:10]:
    pid, title, vf_profile, vf_chunks, has_abs, has_intro, has_method, has_concl = p
    title_short = title[:50] + "..." if title and len(title) > 50 else title
    print(f"\n📄 {pid}")
    print(f"   Title: {title_short}")
    print(f"   vf_profile_exists: {vf_profile}")
    print(f"   vf_chunks_generated: {vf_chunks}")
    print(f"   章节标记: abs={has_abs}, intro={has_intro}, method={has_method}, concl={has_concl}")

# 在 Qdrant 验证这些论文的实际数据
print("\n" + "=" * 70)
print("Qdrant 实际数据验证:")
print("=" * 70)

for p in papers[:5]:
    pid = p[0]
    print(f"\n📄 {pid}")
    
    # 检查 vf_profiles
    try:
        response = requests.post(
            f"{QDRANT_URL}/collections/vf_profiles/points/scroll",
            json={
                "filter": {"must": [{"key": "paper_id", "match": {"value": pid}}]},
                "limit": 20,
                "with_payload": True,
                "with_vector": False
            }
        )
        if response.status_code == 200:
            points = response.json().get("result", {}).get("points", [])
            print(f"   vf_profiles: {len(points)} records")
            
            if points:
                # 显示 chunk_ids
                chunk_ids = [pt.get("payload", {}).get("chunk_id", "?") for pt in points]
                print(f"   chunk_ids: {chunk_ids[:8]}...")
                
                # 检查 meta
                meta_point = next((pt for pt in points if pt.get("payload", {}).get("chunk_id") == "meta"), None)
                if meta_point:
                    meta = meta_point.get("payload", {}).get("meta", {})
                    print(f"   meta keys: {list(meta.keys())}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 检查 academic_papers
    try:
        response = requests.post(
            f"{QDRANT_URL}/collections/academic_papers/points/scroll",
            json={
                "filter": {"must": [{"key": "paper_name", "match": {"value": pid}}]},
                "limit": 50,
                "with_payload": ["section", "chunk_index"],
                "with_vector": False
            }
        )
        if response.status_code == 200:
            points = response.json().get("result", {}).get("points", [])
            print(f"   academic_papers: {len(points)} chunks")
            
            if points:
                sections = {}
                for pt in points:
                    sec = pt.get("payload", {}).get("section", "unknown")
                    sections[sec] = sections.get(sec, 0) + 1
                print(f"   sections: {sections}")
    except Exception as e:
        print(f"   Error: {e}")

# 检查一下 chunks 文件夹是否真的不存在
print("\n" + "=" * 70)
print("文件系统验证:")
print("=" * 70)

for p in papers[:5]:
    pid = p[0]
    
    # 尝试各种可能的文件夹名
    possible_names = [pid, pid.replace("_", "-"), pid.lower()]
    found = False
    
    for name in possible_names:
        folder = chunks_dir / name
        if folder.exists():
            files = list(folder.iterdir())
            print(f"✅ {pid}: 找到文件夹 ({len(files)} files)")
            found = True
            break
    
    if not found:
        print(f"❌ {pid}: 确实无 chunks 文件夹")

conn.close()

print("\n" + "=" * 70)
print("结论")
print("=" * 70)
