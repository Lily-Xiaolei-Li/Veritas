from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
c = QdrantClient(host='localhost', port=6333)

# Find all 2015 papers
results, _ = c.scroll('vf_profiles', scroll_filter=Filter(must=[
    FieldCondition(key='chunk_id', match=MatchValue(value='meta')),
    FieldCondition(key='meta.year', match=MatchValue(value=2015))
]), limit=50, with_payload=['meta', 'paper_id'])

print(f'Found {len(results)} papers from 2015')
for p in results:
    meta = p.payload.get('meta', {})
    authors = meta.get('authors', ['?'])
    first_author = authors[0] if authors else '?'
    title = meta.get('title', '?')[:50]
    print(f"  {p.payload.get('paper_id')}: {first_author} - {title}")
