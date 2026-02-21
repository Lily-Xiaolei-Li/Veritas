import json

with open('data/library_sync/sync_results.json') as f:
    data = json.load(f)

pending = [x for x in data if x.get('item_id') == 'pending']
print(f'Total pending: {len(pending)}')
print('\n--- Sample 10 ---\n')

for p in pending[:10]:
    print(f"File: {p['filename']}")
    ext = p.get('extracted', {})
    authors = ext.get('authors', [])
    first_author = authors[0] if authors else 'N/A'
    year = ext.get('year', 'N/A')
    journal = ext.get('journal', 'N/A')
    reason = p.get('reason', 'unknown')
    print(f"  Extracted: {first_author} ({year}) - {journal}")
    print(f"  Reason: {reason}")
    print()
