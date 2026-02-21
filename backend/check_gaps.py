import sqlite3
conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print("=" * 60)
print("数据差距分析")
print("=" * 60)

# 1. Cross-check: In Excel but not in VF Store
cur.execute("""SELECT COUNT(*) FROM papers 
    WHERE in_excel_index = 1 AND (in_vf_store = 0 OR in_vf_store IS NULL)""")
excel_not_vf = cur.fetchone()[0]
print(f"\n📊 在 Excel 但不在 VF Store: {excel_not_vf} 篇")

# 2. In VF Store but not in Excel
cur.execute("""SELECT COUNT(*) FROM papers 
    WHERE in_vf_store = 1 AND (in_excel_index = 0 OR in_excel_index IS NULL)""")
vf_not_excel = cur.fetchone()[0]
print(f"📊 在 VF Store 但不在 Excel: {vf_not_excel} 篇")

# 3. Has chunks but not in VF Store
cur.execute("""SELECT COUNT(*) FROM papers 
    WHERE has_chunks_folder = 1 AND (in_vf_store = 0 OR in_vf_store IS NULL)""")
chunks_not_vf = cur.fetchone()[0]
print(f"📊 有 chunks 但不在 VF Store: {chunks_not_vf} 篇")

# 4. In VF Store but no chunks
cur.execute("""SELECT COUNT(*) FROM papers 
    WHERE in_vf_store = 1 AND (has_chunks_folder = 0 OR has_chunks_folder IS NULL)""")
vf_no_chunks = cur.fetchone()[0]
print(f"📊 在 VF Store 但无 chunks: {vf_no_chunks} 篇")

# 5. Papers with all key sections
cur.execute("""SELECT COUNT(*) FROM papers 
    WHERE has_abstract = 1 AND has_introduction = 1 
    AND has_methodology = 1 AND has_conclusion = 1""")
complete = cur.fetchone()[0]
print(f"\n✅ 四个核心章节齐全: {complete} 篇")

# 6. Papers with no sections at all
cur.execute("""SELECT COUNT(*) FROM papers 
    WHERE (has_abstract = 0 OR has_abstract IS NULL)
    AND (has_introduction = 0 OR has_introduction IS NULL)
    AND (has_methodology = 0 OR has_methodology IS NULL)
    AND (has_conclusion = 0 OR has_conclusion IS NULL)""")
no_sections = cur.fetchone()[0]
print(f"❌ 无任何章节: {no_sections} 篇")

# 7. Year distribution
print("\n📅 年份分布:")
cur.execute("""SELECT year, COUNT(*) FROM papers 
    WHERE year IS NOT NULL 
    GROUP BY year ORDER BY year DESC LIMIT 10""")
for row in cur.fetchall():
    print(f"   {row[0]}: {row[1]} 篇")

# 8. Papers without year
cur.execute("SELECT COUNT(*) FROM papers WHERE year IS NULL")
no_year = cur.fetchone()[0]
print(f"   无年份: {no_year} 篇")

# 9. Check chunk counts
cur.execute("""SELECT 
    MIN(lib_chunk_count), 
    MAX(lib_chunk_count), 
    AVG(lib_chunk_count) 
    FROM papers WHERE lib_chunk_count > 0""")
stats = cur.fetchone()
print(f"\n📦 Chunk 统计 (有 chunks 的论文):")
print(f"   最少: {stats[0]}, 最多: {stats[1]}, 平均: {stats[2]:.1f}")

# 10. Papers with very few chunks (potential quality issue)
cur.execute("""SELECT paper_id, lib_chunk_count FROM papers 
    WHERE lib_chunk_count > 0 AND lib_chunk_count < 3
    LIMIT 5""")
few_chunks = cur.fetchall()
if few_chunks:
    print(f"\n⚠️ Chunks 很少 (<3) 的论文:")
    for p in few_chunks:
        print(f"   - {p[0]}: {p[1]} chunks")

conn.close()
