import json
from datetime import datetime

with open('data/library_sync/sync_results.json') as f:
    data = json.load(f)

first = datetime.fromisoformat(data[0]['timestamp'])
last = datetime.fromisoformat(data[-1]['timestamp'])
duration = (last - first).total_seconds()

print(f"First: {data[0]['timestamp']}")
print(f"Last: {data[-1]['timestamp']}")
print(f"Count: {len(data)}")
print(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
print(f"Per paper: {duration/len(data):.1f} seconds")
