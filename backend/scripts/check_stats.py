"""统计检查"""
import sqlite3

conn = sqlite3.connect(r"C:\Users\Barry Li (UoN)\clawd\projects\Agent-B-Research\backend\data\central_index.sqlite")
cur = conn.cursor()

# 统计
cur.execute("SELECT COUNT(*) FROM papers WHERE paper_id LIKE 'CHUNKS_%'")
total = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM papers WHERE paper_id LIKE 'CHUNKS_%' AND in_vf_store = 1")
in_vf = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM papers WHERE paper_id LIKE 'CHUNKS_%' AND vf_profile_exists = 1")
has_profile = cur.fetchone()[0]

print(f"SQLite Priority 1 论文统计:")
print(f"  总数: {total}")
print(f"  in_vf_store=1: {in_vf}")
print(f"  vf_profile_exists=1: {has_profile}")

conn.close()
