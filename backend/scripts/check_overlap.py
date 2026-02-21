from qdrant_client import QdrantClient
c = QdrantClient(host='localhost', port=6333)

# Count VF meta chunks (= number of papers in VF)
offset = None
vf_count = 0
vf_in_library = 0
while True:
    results, offset = c.scroll('vf_profiles', scroll_filter={'must': [{'key': 'chunk_id', 'match': {'value': 'meta'}}]}, limit=500, with_payload=['meta'], offset=offset)
    vf_count += len(results)
    for p in results:
        if p.payload.get('meta', {}).get('in_library'):
            vf_in_library += 1
    if offset is None:
        break

print(f'VF Store total papers: {vf_count}')
print(f'VF papers marked in_library=True: {vf_in_library}')
print(f'VF papers NOT in library: {vf_count - vf_in_library}')
