import json

with open('data/library_sync/sync_progress.json') as f:
    p = json.load(f)

print(f"Processed: {len(p.get('processed', []))}")
print(f"Matched: {len(p.get('matched', []))}")
print(f"Pending: {len(p.get('pending', []))}")
print(f"Exceptions: {len(p.get('exceptions', []))}")
