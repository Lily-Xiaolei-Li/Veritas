"""Show VF profiles without source_file."""
from qdrant_client import QdrantClient
client = QdrantClient(host='localhost', port=6333)

# Get VF profiles
results, _ = client.scroll('vf_profiles', scroll_filter={'must': [{'key': 'chunk_id', 'match': {'value': 'meta'}}]}, limit=30, with_payload=['paper_id', 'meta'])

print('VF profiles without source_file:')
print('=' * 70)
count = 0
for p in results:
    meta = p.payload.get('meta', {})
    if not meta.get('source_file') and count < 10:
        title = meta.get('title', 'N/A')
        authors = meta.get('authors', [])
        print(f"paper_id: {p.payload.get('paper_id')}")
        print(f"  title: {title[:70] if title else 'N/A'}...")
        print(f"  authors: {authors[:2] if authors else 'N/A'}")
        print(f"  year: {meta.get('year')}")
        print(f"  in_library: {meta.get('in_library')}")
        print()
        count += 1

print(f'Shown: {count} profiles without source_file')
