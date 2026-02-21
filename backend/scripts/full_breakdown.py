"""Full breakdown of Library and VF Store status."""
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from pathlib import Path
import json

client = QdrantClient(host='localhost', port=6333)

print('=' * 60)
print('LIBRARY SIDE')
print('=' * 60)

# Library files
library_path = Path(r'C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed')
all_files = list(library_path.glob('*.md'))
book_chapters = [f for f in all_files if '978-3-' in f.name]
non_book = [f for f in all_files if '978-3-' not in f.name]
print(f'Total MD files: {len(all_files)}')
print(f'  - Book chapters (978-3-): {len(book_chapters)}')
print(f'  - Non-book chapters: {len(non_book)}')

# Progress file
progress_file = Path('data/library_sync/sync_progress.json')
if progress_file.exists():
    progress = json.loads(progress_file.read_text())
    processed = progress.get('processed', [])
    matched = progress.get('matched', [])
    pending = progress.get('pending', [])
    exceptions = progress.get('exceptions', [])
    print(f'\nMethod 1 Progress:')
    print(f'  Processed: {len(processed)}')
    print(f'  Matched (got item_id): {len(matched)}')
    print(f'  Pending (no VF match): {len(pending)}')
    print(f'  Exceptions: {len(exceptions)}')
    print(f'  Unprocessed: {len(non_book) - len(processed)}')

print()
print('=' * 60)
print('VF STORE SIDE')
print('=' * 60)

# VF profiles
all_meta = []
offset = None
while True:
    results, offset = client.scroll(
        'vf_profiles', 
        scroll_filter=Filter(must=[FieldCondition(key='chunk_id', match=MatchValue(value='meta'))]), 
        limit=500, 
        with_payload=True, 
        offset=offset
    )
    all_meta.extend(results)
    if offset is None:
        break

total_vf = len(all_meta)
in_library_true = [p for p in all_meta if p.payload.get('meta', {}).get('in_library') == True]
in_library_false = [p for p in all_meta if p.payload.get('meta', {}).get('in_library') == False]
in_library_none = [p for p in all_meta if p.payload.get('meta', {}).get('in_library') is None]

with_item_id = [p for p in all_meta if p.payload.get('meta', {}).get('item_id')]
without_item_id = [p for p in all_meta if not p.payload.get('meta', {}).get('item_id')]

in_lib_with_id = [p for p in in_library_true if p.payload.get('meta', {}).get('item_id')]
in_lib_without_id = [p for p in in_library_true if not p.payload.get('meta', {}).get('item_id')]

print(f'Total VF profiles: {total_vf}')
print(f'  - in_library=True: {len(in_library_true)}')
print(f'  - in_library=False: {len(in_library_false)}')
print(f'  - in_library=None/missing: {len(in_library_none)}')
print()
print(f'Item ID status (all):')
print(f'  - With item_id: {len(with_item_id)}')
print(f'  - Without item_id: {len(without_item_id)}')
print()
print(f'in_library=True breakdown:')
print(f'  - With item_id (matched): {len(in_lib_with_id)}')
print(f'  - Without item_id (Y for Method 2): {len(in_lib_without_id)}')

print()
print('=' * 60)
print('ANALYSIS')
print('=' * 60)
print(f'Library non-book: {len(non_book)}')
print(f'VF in_library=True: {len(in_library_true)}')
print(f'Gap (Library has but VF does not): {len(non_book) - len(in_library_true)}')
print()
print(f'Library matched: {len(matched)}')
print(f'VF with item_id: {len(with_item_id)}')
print(f'Difference: {len(matched) - len(with_item_id)} (duplicates in Library)')
