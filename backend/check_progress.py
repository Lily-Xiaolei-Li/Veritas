"""检查修复进度"""
import sqlite3
import requests

QDRANT_URL = "http://localhost:6333"

print("=" * 50)
print("Priority 1 修复进度检查")
print("=" * 50)

# SQLite 检查
conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

cur.execute('SELECT COUNT(*) FROM papers WHERE in_vf_store = 1')
in_vf = cur.fetchone()[0]
print(f"\n📊 SQLite 状态:")
print(f"   in_vf_store=1: {in_vf} 篇")

cur.execute("SELECT COUNT(*) FROM papers WHERE paper_id LIKE 'CHUNKS_%'")
total_chunks = cur.fetchone()[0]
print(f"   CHUNKS_ 论文总数: {total_chunks} 篇")

cur.execute("SELECT COUNT(*) FROM papers WHERE paper_id LIKE 'CHUNKS_%' AND in_vf_store = 1")
chunks_in_vf = cur.fetchone()[0]
print(f"   CHUNKS_ 已在 VF: {chunks_in_vf} 篇")

conn.close()

# Qdrant 检查
print(f"\n📊 Qdrant 状态:")
try:
    r = requests.get(f"{QDRANT_URL}/collections/vf_profiles")
    data = r.json()
    print(f"   vf_profiles points: {data['result']['points_count']}")
except Exception as e:
    print(f"   Error: {e}")

try:
    r = requests.get(f"{QDRANT_URL}/collections/academic_papers")
    data = r.json()
    print(f"   academic_papers points: {data['result']['points_count']}")
except Exception as e:
    print(f"   Error: {e}")

# 测试一个 CHUNKS_ 论文
print(f"\n🧪 测试 section_lookup:")
try:
    from tools import lookup_introduction
    
    # 找一个 CHUNKS_ 论文测试
    conn = sqlite3.connect('data/central_index.sqlite')
    cur = conn.cursor()
    cur.execute("SELECT paper_id FROM papers WHERE paper_id LIKE 'CHUNKS_%' LIMIT 1")
    test_pid = cur.fetchone()[0]
    conn.close()
    
    result = lookup_introduction(test_pid)
    if result.get('found'):
        print(f"   ✅ {test_pid[:40]}... : {result['char_count']} chars")
    else:
        print(f"   ❌ {test_pid[:40]}... : Not found")
except Exception as e:
    print(f"   Error: {e}")
