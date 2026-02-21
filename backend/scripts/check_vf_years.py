from qdrant_client import QdrantClient
c = QdrantClient(host='localhost', port=6333)

# Check what years are in VF store
results, _ = c.scroll('vf_profiles', scroll_filter={'must': [{'key': 'chunk_id', 'match': {'value': 'meta'}}]}, limit=500, with_payload=['meta'])

years = {}
all_papers = []
for p in results:
    meta = p.payload.get('meta', {})
    y = meta.get('year')
    if y:
        years[y] = years.get(y, 0) + 1
    all_papers.append(meta)

print('VF Store years distribution (top 15):')
for y in sorted(years.keys(), reverse=True)[:15]:
    print(f'  {y}: {years[y]} papers')

print(f'\nTotal in sample: {len(all_papers)}')

# Check for Ahrens 2006
print('\nLooking for specific papers...')
for meta in all_papers:
    if meta.get('year') == 2006:
        authors = meta.get('authors', [])
        if any('ahrens' in str(a).lower() for a in authors):
            title = meta.get('title', 'N/A')
            print(f'  Ahrens 2006: {title[:60]}')

# Check for De Villiers 2025
for meta in all_papers:
    if meta.get('year') == 2025:
        authors = meta.get('authors', [])
        if any('villiers' in str(a).lower() for a in authors):
            title = meta.get('title', 'N/A')
            print(f'  De Villiers 2025: {title[:60]}')
