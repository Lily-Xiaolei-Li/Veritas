import sqlite3
conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

# Get tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('=== Tables ===')
for t in cur.fetchall():
    print(t[0])

print()
print('=== Row counts ===')
for table in ['chunks', 'papers', 'sections', 'paper_metadata', 'vf_profiles']:
    try:
        cur.execute(f'SELECT COUNT(*) FROM {table}')
        print(f'{table}: {cur.fetchone()[0]}')
    except Exception as e:
        print(f'{table}: ERROR - {e}')

# Check papers table schema
print()
print('=== Papers table schema ===')
cur.execute("PRAGMA table_info(papers)")
for col in cur.fetchall():
    print(f"  {col[1]} ({col[2]})")

# Sample papers
print()
print('=== Sample papers ===')
cur.execute("SELECT * FROM papers LIMIT 3")
cols = [d[0] for d in cur.description]
print(f"Columns: {cols}")
for row in cur.fetchall():
    print(row[:3])

conn.close()
