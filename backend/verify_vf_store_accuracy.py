"""
验证 SQLite in_vf_store 标记的准确性
"""
import requests
import sqlite3
from collections import defaultdict

QDRANT_URL = "http://localhost:6333"

conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print("=" * 70)
print("验证 in_vf_store 标记准确性")
print("=" * 70)

# 获取 SQLite 中标记为 in_vf_store=1 的论文
cur.execute("SELECT paper_id FROM papers WHERE in_vf_store = 1")
sqlite_vf_papers = set(r[0] for r in cur.fetchall())
print(f"\nSQLite 标记在 VF Store: {len(sqlite_vf_papers)} 篇")

# 获取 Qdrant vf_profiles 中的所有 paper_id
response = requests.post(
    f"{QDRANT_URL}/collections/vf_profiles/points/scroll",
    json={
        "limit": 10000,
        "with_payload": ["paper_id"],
        "with_vector": False
    }
)

qdrant_vf_papers = set()
if response.status_code == 200:
    points = response.json().get("result", {}).get("points", [])
    for p in points:
        pid = p.get("payload", {}).get("paper_id")
        if pid:
            qdrant_vf_papers.add(pid)

print(f"Qdrant vf_profiles 实际存在: {len(qdrant_vf_papers)} 篇")

# 获取 Qdrant academic_papers 中的所有 paper_name
response = requests.post(
    f"{QDRANT_URL}/collections/academic_papers/points/scroll",
    json={
        "limit": 200000,
        "with_payload": ["paper_name"],
        "with_vector": False
    }
)

qdrant_academic_papers = set()
if response.status_code == 200:
    points = response.json().get("result", {}).get("points", [])
    for p in points:
        pname = p.get("payload", {}).get("paper_name")
        if pname:
            qdrant_academic_papers.add(pname)

print(f"Qdrant academic_papers 实际存在: {len(qdrant_academic_papers)} 篇")

# 交叉检查
in_sqlite_not_qdrant = sqlite_vf_papers - qdrant_vf_papers
in_qdrant_not_sqlite = qdrant_vf_papers - sqlite_vf_papers

print(f"\n📊 交叉检查结果:")
print(f"  在 SQLite 但不在 Qdrant vf_profiles: {len(in_sqlite_not_qdrant)}")
print(f"  在 Qdrant vf_profiles 但不在 SQLite: {len(in_qdrant_not_sqlite)}")

# 检查 academic_papers 与 SQLite 的对应
# 需要考虑 paper_name 可能与 paper_id 格式不完全相同
matches = 0
partial_matches = 0

for pid in list(sqlite_vf_papers)[:100]:
    if pid in qdrant_academic_papers:
        matches += 1
    else:
        # 尝试部分匹配
        for pname in qdrant_academic_papers:
            if pid[:30].lower() in pname.lower() or pname[:30].lower() in pid.lower():
                partial_matches += 1
                break

print(f"\n📊 academic_papers 匹配检查 (前100篇):")
print(f"  精确匹配: {matches}")
print(f"  部分匹配: {partial_matches}")

# 样本：在 SQLite 标记但实际不在 Qdrant 的
print(f"\n🔍 样本：SQLite 标记在 VF 但实际不在 Qdrant vf_profiles:")
for pid in list(in_sqlite_not_qdrant)[:10]:
    print(f"  - {pid}")

# 样本：在 Qdrant 但不在 SQLite 的
print(f"\n🔍 样本：在 Qdrant vf_profiles 但 SQLite 未标记:")
for pid in list(in_qdrant_not_sqlite)[:10]:
    print(f"  - {pid}")

conn.close()

print("\n" + "=" * 70)
print("结论")
print("=" * 70)
print(f"""
问题发现：
1. SQLite 的 in_vf_store 标记不准确
2. {len(in_sqlite_not_qdrant)} 篇标记在 VF 但实际不存在
3. {len(in_qdrant_not_sqlite)} 篇在 Qdrant 但 SQLite 未标记

建议：
- 重新同步 SQLite 索引与 Qdrant 实际数据
- 统一 paper_id 格式
""")
