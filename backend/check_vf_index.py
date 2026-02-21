import sqlite3

conn = sqlite3.connect('data/vf_metadata.sqlite')
cur = conn.cursor()

print('=== VF Store Index 完整度报告 ===\n')

# 表结构
cur.execute('PRAGMA table_info(vf_profiles_index)')
cols = cur.fetchall()
print('表结构:')
for c in cols:
    print(f'  {c[1]:20} {c[2]}')

print()

# 总数
cur.execute('SELECT COUNT(*) FROM vf_profiles_index')
total = cur.fetchone()[0]
print(f'总记录数: {total}')

# 完整度
checks = [
    ('in_library=1', 'in_library'),
    ('profile_exists=1', 'profile_exists'),
    ('chunks_generated=1', 'chunks_generated'),
    ("authors_json IS NOT NULL AND authors_json != ''", 'has authors'),
    ('year IS NOT NULL', 'has year'),
    ("title IS NOT NULL AND title != ''", 'has title'),
    ('meta_json IS NOT NULL', 'has meta_json'),
]

print('\n完整度:')
for condition, label in checks:
    cur.execute(f'SELECT COUNT(*) FROM vf_profiles_index WHERE {condition}')
    count = cur.fetchone()[0]
    pct = count/total*100
    print(f'  {label:20} {count:4}/{total} ({pct:.1f}%)')

# 缺失的
print('\n缺失项:')
cur.execute('SELECT paper_id, title FROM vf_profiles_index WHERE in_library=0 LIMIT 5')
rows = cur.fetchall()
print(f'  not in_library (sample): {len(rows)} shown')
for r in rows:
    print(f'    - {r[0]}: {r[1][:50] if r[1] else "N/A"}...')

conn.close()
