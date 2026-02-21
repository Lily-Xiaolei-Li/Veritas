"""Check filename consistency between academic_papers and vf_profiles."""
from qdrant_client import QdrantClient

client = QdrantClient(host='localhost', port=6333)

# Get filenames from academic_papers
print('=== academic_papers filenames ===')
ap_files = set()
offset = None
count = 0
while True:
    results, offset = client.scroll('academic_papers', limit=1000, with_payload=['filename'], offset=offset)
    for p in results:
        fn = p.payload.get('filename')
        if fn:
            ap_files.add(fn)
    count += len(results)
    if offset is None:
        break

print(f'Total points scanned: {count}')
print(f'Unique filenames: {len(ap_files)}')
print(f'Sample: {list(ap_files)[:3]}')

# Get source_file from vf_profiles
print()
print('=== vf_profiles source_files ===')
vf_files = set()
vf_no_source = 0
offset = None
while True:
    results, offset = client.scroll('vf_profiles', scroll_filter={'must': [{'key': 'chunk_id', 'match': {'value': 'meta'}}]}, limit=500, with_payload=['meta', 'paper_id'], offset=offset)
    for p in results:
        meta = p.payload.get('meta', {})
        sf = meta.get('source_file')
        if sf:
            vf_files.add(sf)
        else:
            vf_no_source += 1
    if offset is None:
        break

print(f'Profiles with source_file: {len(vf_files)}')
print(f'Profiles WITHOUT source_file: {vf_no_source}')
print(f'Sample: {list(vf_files)[:3]}')

# Compare
print()
print('=== Comparison ===')
common = ap_files & vf_files
only_ap = ap_files - vf_files
only_vf = vf_files - ap_files

print(f'In both: {len(common)}')
print(f'Only in academic_papers: {len(only_ap)}')
print(f'Only in vf_profiles: {len(only_vf)}')

if only_vf:
    print(f'\nVF files not in academic_papers (sample): {list(only_vf)[:5]}')
