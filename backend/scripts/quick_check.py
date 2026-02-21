"""Quick check of filename formats."""
from qdrant_client import QdrantClient
client = QdrantClient(host='localhost', port=6333)

# academic_papers sample
print('=== academic_papers sample (first 5) ===')
results, _ = client.scroll('academic_papers', limit=5, with_payload=['filename', 'paper_name'])
for p in results:
    print(f"  filename: {p.payload.get('filename')}")
    print(f"  paper_name: {p.payload.get('paper_name')}")
    print()

# Count unique filenames in academic_papers (sample 1000)
print('=== academic_papers filename stats ===')
results, _ = client.scroll('academic_papers', limit=1000, with_payload=['filename'])
filenames = [p.payload.get('filename') for p in results if p.payload.get('filename')]
unique = set(filenames)
print(f"Points sampled: {len(results)}")
print(f"Unique filenames in sample: {len(unique)}")

# vf_profiles stats
print()
print('=== vf_profiles source_file stats ===')
results, _ = client.scroll('vf_profiles', scroll_filter={'must': [{'key': 'chunk_id', 'match': {'value': 'meta'}}]}, limit=500, with_payload=['meta', 'paper_id'])
with_sf = 0
without_sf = 0
for p in results:
    meta = p.payload.get('meta', {})
    if meta.get('source_file'):
        with_sf += 1
    else:
        without_sf += 1

print(f"Meta chunks sampled: {len(results)}")
print(f"With source_file: {with_sf}")
print(f"WITHOUT source_file: {without_sf}")
