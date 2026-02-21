import sqlite3
conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print('=== Step 4 Excel Merge 验证 ===')
print()

# 总记录数（应该不变）
cur.execute('SELECT COUNT(*) FROM papers')
print(f'总记录数: {cur.fetchone()[0]} (应该仍是 ~1290)')

# in_excel_index
cur.execute('SELECT COUNT(*) FROM papers WHERE in_excel_index = 1')
print(f'in_excel_index=1: {cur.fetchone()[0]}')

# doi 填充
cur.execute("SELECT COUNT(*) FROM papers WHERE doi IS NOT NULL AND doi != ''")
doi_count = cur.fetchone()[0]
print(f'有 doi: {doi_count}')

# canonical_id 填充
cur.execute('SELECT COUNT(*) FROM papers WHERE canonical_id IS NOT NULL')
canonical_count = cur.fetchone()[0]
print(f'有 canonical_id: {canonical_count}')

# pdf_filename 填充
cur.execute('SELECT COUNT(*) FROM papers WHERE pdf_filename IS NOT NULL')
pdf_count = cur.fetchone()[0]
print(f'有 pdf_filename: {pdf_count}')

print()
print('=== 来源分布更新 ===')
cur.execute('SELECT COUNT(*) FROM papers WHERE in_vf_store = 1')
print(f'in_vf_store: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(*) FROM papers WHERE in_library_index = 1')
print(f'in_library_index: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(*) FROM papers WHERE in_excel_index = 1')
print(f'in_excel_index: {cur.fetchone()[0]}')
cur.execute('SELECT COUNT(*) FROM papers WHERE has_chunks_folder = 1')
print(f'has_chunks_folder: {cur.fetchone()[0]}')

print()
print('=== 抽样验证 (有 Excel 数据的记录) ===')
cur.execute('''
    SELECT paper_id, title, doi, canonical_id, pdf_filename 
    FROM papers 
    WHERE in_excel_index=1 AND doi IS NOT NULL 
    LIMIT 3
''')
for row in cur.fetchall():
    print(f'paper_id: {row[0]}')
    title = row[1][:50] + '...' if row[1] and len(row[1]) > 50 else row[1]
    print(f'  title: {title}')
    print(f'  doi: {row[2]}')
    print(f'  canonical_id: {row[3][:50]}...' if row[3] and len(row[3]) > 50 else f'  canonical_id: {row[3]}')
    print(f'  pdf_filename: {row[4][:60]}...' if row[4] and len(row[4]) > 60 else f'  pdf_filename: {row[4]}')
    print()

conn.close()
