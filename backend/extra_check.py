import sqlite3
conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print('=== 额外质量检查 ===')

# 检查一些样本记录的实际内容
print()
print('--- 3源记录样本 ---')
cur.execute('''
    SELECT id, paper_id, title, year, in_vf_store, in_library_index, 
           has_chunks_folder, chunks_folder, item_ids_json
    FROM papers 
    WHERE (in_vf_store + in_library_index + has_chunks_folder) = 3 
    LIMIT 3
''')
for row in cur.fetchall():
    print(f'id={row[0]}, paper_id={row[1]}')
    title = row[2][:50] + '...' if row[2] and len(row[2]) > 50 else row[2]
    print(f'  title: {title}')
    print(f'  year: {row[3]}, vf={row[4]}, lib={row[5]}, chunks={row[6]}')
    print(f'  chunks_folder: {row[7]}')
    print(f'  item_ids: {row[8]}')
    print()

print('--- 1源记录样本 (只有 VF) ---')
cur.execute('''
    SELECT id, paper_id, title, year 
    FROM papers 
    WHERE in_vf_store=1 AND in_library_index=0 AND has_chunks_folder=0 
    LIMIT 3
''')
for row in cur.fetchall():
    print(f'id={row[0]}, paper_id={row[1]}, year={row[3]}')
    title = row[2][:60] + '...' if row[2] and len(row[2]) > 60 else row[2]
    print(f'  title: {title}')
    print()

print('--- 1源记录样本 (只有 Chunks) ---')
cur.execute('''
    SELECT id, paper_id, title, year, chunks_folder 
    FROM papers 
    WHERE in_vf_store=0 AND in_library_index=0 AND has_chunks_folder=1 
    LIMIT 3
''')
for row in cur.fetchall():
    print(f'id={row[0]}, paper_id={row[1]}, year={row[3]}')
    title = row[2][:60] + '...' if row[2] and len(row[2]) > 60 else row[2]
    print(f'  title: {title}')
    print(f'  chunks_folder: {row[4]}')
    print()

# 检查字段完整度
print('--- 字段完整度 ---')
fields = ['title', 'year', 'journal', 'paper_type', 'primary_method', 'doi', 'chunks_folder']
for f in fields:
    cur.execute(f'SELECT COUNT(*) FROM papers WHERE {f} IS NOT NULL AND {f} != ""')
    count = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM papers')
    total = cur.fetchone()[0]
    pct = count / total * 100
    print(f'  {f}: {count}/{total} ({pct:.1f}%)')

conn.close()
