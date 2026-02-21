"""
测试在 VF Store 但无 chunks 文件夹的论文
"""
from tools import lookup_introduction, lookup_all_sections
import sqlite3

conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

# 获取无 chunks 文件夹但在 VF Store 的论文
cur.execute("""
SELECT paper_id FROM papers 
WHERE in_vf_store = 1 AND (has_chunks_folder = 0 OR has_chunks_folder IS NULL)
LIMIT 5
""")

papers = [r[0] for r in cur.fetchall()]
conn.close()

print("=" * 70)
print("测试：在 VF Store 但无 chunks 文件夹的论文")
print("=" * 70)

for pid in papers:
    print(f"\n📄 {pid}")
    
    try:
        result = lookup_introduction(pid)
        if result.get('found'):
            print(f"   ✅ Introduction: {result.get('char_count')} chars")
            print(f"   Preview: {result['content'][:100]}...")
        else:
            print(f"   ❌ Introduction: Not found")
    except Exception as e:
        print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("结论：这些论文的章节数据存在于 Qdrant VF Store，")
print("但 library-rag/data/chunks/ 没有对应的 MD 文件。")
print("=" * 70)
