"""Fix VF profiles: add source_file field by matching titles to library files."""
from qdrant_client import QdrantClient
from pathlib import Path
import sys

def norm(s: str) -> str:
    return ''.join(c.lower() for c in s if c.isalnum())

def main():
    client = QdrantClient(host='localhost', port=6333)
    library_path = Path(r'C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed')

    # Build lookup: normalized title -> filename
    files = list(library_path.rglob('*.md'))
    file_by_norm = {}
    for f in files:
        # Full stem
        file_by_norm[norm(f.stem)] = f.name
        # Title part only (after Author_Year_)
        parts = f.stem.split('_', 2)
        if len(parts) >= 3:
            file_by_norm[norm(parts[2])[:50]] = f.name

    print(f'Library files indexed: {len(files)}')

    # Get all meta chunks
    offset = None
    updated = 0
    skipped = 0
    not_found = 0
    batch_updates = []

    while True:
        results, offset = client.scroll(
            'vf_profiles',
            scroll_filter={'must': [{'key': 'chunk_id', 'match': {'value': 'meta'}}]},
            limit=100,
            with_payload=True,
            offset=offset
        )
        if not results:
            break

        for p in results:
            meta = p.payload.get('meta', {})
            if meta.get('source_file'):
                skipped += 1
                continue

            title = meta.get('title', '')
            if not title:
                not_found += 1
                continue

            # Try to find matching file
            norm_title = norm(title)[:50]
            matched_file = file_by_norm.get(norm_title)

            if matched_file:
                meta['source_file'] = matched_file
                batch_updates.append((p.id, {'meta': meta}))
                updated += 1
            else:
                not_found += 1

        # Batch update every 50
        if len(batch_updates) >= 50:
            for point_id, payload in batch_updates:
                client.set_payload('vf_profiles', payload=payload, points=[point_id])
            print(f'Updated {updated}...')
            batch_updates = []

        if offset is None:
            break

    # Final batch
    for point_id, payload in batch_updates:
        client.set_payload('vf_profiles', payload=payload, points=[point_id])

    print(f'\n=== Done ===')
    print(f'Updated: {updated}')
    print(f'Already had source_file: {skipped}')
    print(f'Not found: {not_found}')

if __name__ == '__main__':
    main()
