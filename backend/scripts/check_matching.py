"""Check if we can match VF profiles to academic_papers by title."""
from qdrant_client import QdrantClient
client = QdrantClient(host='localhost', port=6333)

def norm(s):
    """Normalize string for matching."""
    return ''.join(c.lower() for c in s if c.isalnum())

# Get paper_names from academic_papers (unique)
print('Loading academic_papers paper_names...')
ap_names = set()
offset = None
while True:
    results, offset = client.scroll('academic_papers', limit=1000, with_payload=['paper_name'], offset=offset)
    for p in results:
        pn = p.payload.get('paper_name')
        if pn:
            ap_names.add(pn)
    if offset is None or len(ap_names) > 2000:  # Limit for speed
        break

print(f'Unique paper_names: {len(ap_names)}')

# Build normalized lookup
ap_norm = {norm(pn): pn for pn in ap_names}

# Check VF profiles without source_file
print()
print('Checking VF profiles without source_file...')
offset = None
matched = 0
not_matched = 0
sample_unmatched = []

while True:
    results, offset = client.scroll('vf_profiles', scroll_filter={'must': [{'key': 'chunk_id', 'match': {'value': 'meta'}}]}, limit=200, with_payload=['paper_id', 'meta'], offset=offset)
    
    for p in results:
        meta = p.payload.get('meta', {})
        if meta.get('source_file'):
            continue  # Already has source_file
        
        title = meta.get('title', '')
        year = meta.get('year')
        authors = meta.get('authors', [])
        first_author = authors[0].split()[-1] if authors else ''
        
        # Try to match by title in paper_name
        norm_title = norm(title)[:50] if title else ''
        found = False
        
        for ap_norm_name, ap_name in ap_norm.items():
            if norm_title and norm_title in ap_norm_name:
                matched += 1
                found = True
                break
        
        if not found:
            not_matched += 1
            if len(sample_unmatched) < 5:
                sample_unmatched.append({
                    'paper_id': p.payload.get('paper_id'),
                    'title': title[:60] if title else 'N/A',
                    'year': year,
                    'first_author': first_author
                })
    
    if offset is None:
        break

print(f'Matched by title: {matched}')
print(f'Not matched: {not_matched}')
print()
print('Sample unmatched:')
for s in sample_unmatched:
    print(f"  {s['paper_id']}: {s['title']}... ({s['first_author']} {s['year']})")
