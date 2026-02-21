import sqlite3

conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print('=== 数据分布检查 ===')
cur.execute('SELECT COUNT(*) FROM papers')
print(f'总记录: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM papers WHERE in_vf_store = 1')
print(f'in_vf_store: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM papers WHERE in_library_index = 1')
print(f'in_library_index: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM papers WHERE in_excel_index = 1')
print(f'in_excel_index: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM papers WHERE has_chunks_folder = 1')
print(f'has_chunks_folder: {cur.fetchone()[0]}')

print()
print('=== item_id 情况 ===')
cur.execute('SELECT COUNT(*) FROM papers WHERE item_id IS NOT NULL')
print(f'有 item_id: {cur.fetchone()[0]}')

cur.execute('SELECT COUNT(*) FROM papers WHERE item_id IS NULL')
print(f'无 item_id: {cur.fetchone()[0]}')

print()
print('=== 重复检查 ===')
cur.execute("SELECT title, COUNT(*) as cnt FROM papers WHERE title IS NOT NULL GROUP BY title HAVING cnt > 1")
dups = cur.fetchall()
print(f'重复 title 数量: {len(dups)}')
for d in dups[:5]:
    title_preview = d[0][:60] if d[0] else 'N/A'
    print(f'  "{title_preview}..." x{d[1]}')

print()
print('=== 多源覆盖检查 ===')
cur.execute('''
SELECT 
    in_vf_store + in_library_index + in_excel_index + has_chunks_folder as source_count,
    COUNT(*) as papers
FROM papers
GROUP BY source_count
ORDER BY source_count DESC
''')
for row in cur.fetchall():
    print(f'  {row[0]} 个来源: {row[1]} 篇')

print()
print('=== 样本：只有1个来源的记录 ===')
cur.execute('''
SELECT id, item_id, title, in_vf_store, in_library_index, in_excel_index, has_chunks_folder
FROM papers
WHERE in_vf_store + in_library_index + in_excel_index + has_chunks_folder = 1
LIMIT 10
''')
for row in cur.fetchall():
    print(f'id={row[0]}, item_id={row[1]}, title={row[2][:40] if row[2] else "N/A"}...')
    print(f'  vf={row[3]}, lib={row[4]}, excel={row[5]}, chunks={row[6]}')

conn.close()
