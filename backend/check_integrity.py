import sqlite3
conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print("=" * 60)
print("数据完整性检查报告")
print("=" * 60)

# 1. Total papers
cur.execute("SELECT COUNT(*) FROM papers")
total = cur.fetchone()[0]
print(f"\n📚 总论文数: {total}")

# 2. Papers with chunks folder
cur.execute("SELECT COUNT(*) FROM papers WHERE has_chunks_folder = 1")
has_chunks = cur.fetchone()[0]
print(f"   有 chunks 文件夹: {has_chunks} ({100*has_chunks/total:.1f}%)")

# 3. Papers in VF Store
cur.execute("SELECT COUNT(*) FROM papers WHERE in_vf_store = 1")
in_vf = cur.fetchone()[0]
print(f"   在 VF Store: {in_vf} ({100*in_vf/total:.1f}%)")

# 4. Papers in Excel index
cur.execute("SELECT COUNT(*) FROM papers WHERE in_excel_index = 1")
in_excel = cur.fetchone()[0]
print(f"   在 Excel 索引: {in_excel} ({100*in_excel/total:.1f}%)")

# 5. Section coverage
print("\n📑 章节覆盖率:")
for section in ['abstract', 'introduction', 'methodology', 'conclusion']:
    cur.execute(f"SELECT COUNT(*) FROM papers WHERE has_{section} = 1")
    count = cur.fetchone()[0]
    print(f"   {section}: {count} ({100*count/total:.1f}%)")

# 6. Papers missing chunks
cur.execute("SELECT COUNT(*) FROM papers WHERE has_chunks_folder = 0 OR has_chunks_folder IS NULL")
no_chunks = cur.fetchone()[0]
print(f"\n⚠️ 缺少 chunks: {no_chunks} 篇")

# 7. Papers not in VF Store
cur.execute("SELECT COUNT(*) FROM papers WHERE in_vf_store = 0 OR in_vf_store IS NULL")
not_in_vf = cur.fetchone()[0]
print(f"⚠️ 不在 VF Store: {not_in_vf} 篇")

# 8. Papers missing key sections
cur.execute("""SELECT COUNT(*) FROM papers 
    WHERE (has_introduction = 0 OR has_introduction IS NULL) 
    AND has_chunks_folder = 1""")
no_intro = cur.fetchone()[0]
print(f"⚠️ 有 chunks 但无 intro: {no_intro} 篇")

# 9. Sample of problematic papers
print("\n🔍 样本问题论文 (无 chunks):")
cur.execute("SELECT paper_id, title FROM papers WHERE has_chunks_folder = 0 OR has_chunks_folder IS NULL LIMIT 5")
for row in cur.fetchall():
    title = row[1][:50] + "..." if row[1] and len(row[1]) > 50 else row[1]
    print(f"   - {row[0]}: {title}")

# 10. Check canonical_id coverage
cur.execute("SELECT COUNT(*) FROM papers WHERE canonical_id IS NOT NULL AND canonical_id != ''")
has_canonical = cur.fetchone()[0]
print(f"\n🔗 有 canonical_id: {has_canonical} ({100*has_canonical/total:.1f}%)")

# 11. Check for duplicates
cur.execute("""SELECT paper_id, COUNT(*) as cnt FROM papers 
    GROUP BY paper_id HAVING cnt > 1""")
duplicates = cur.fetchall()
if duplicates:
    print(f"\n⚠️ 重复 paper_id: {len(duplicates)} 个")
    for d in duplicates[:3]:
        print(f"   - {d[0]} (出现 {d[1]} 次)")
else:
    print("\n✅ 无重复 paper_id")

conn.close()
