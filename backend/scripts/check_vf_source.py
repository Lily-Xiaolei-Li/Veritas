"""Check VF store source and in_library status."""
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

c = QdrantClient(host='localhost', port=6333)

# Load all VF profiles
print("Loading VF profiles...")
all_vf = []
offset = None
while True:
    results, offset = c.scroll('vf_profiles', scroll_filter=Filter(must=[
        FieldCondition(key='chunk_id', match=MatchValue(value='meta'))
    ]), limit=500, with_payload=['meta', 'paper_id'], offset=offset)
    all_vf.extend(results)
    if offset is None:
        break

print(f"Total VF profiles: {len(all_vf)}")

# Check in_library distribution
in_library_true = 0
in_library_false = 0
in_library_none = 0
has_source_file = 0

for p in all_vf:
    meta = p.payload.get('meta', {})
    il = meta.get('in_library')
    if il is True:
        in_library_true += 1
    elif il is False:
        in_library_false += 1
    else:
        in_library_none += 1
    
    if meta.get('source_file'):
        has_source_file += 1

print(f"\nin_library=True: {in_library_true}")
print(f"in_library=False: {in_library_false}")
print(f"in_library=None/missing: {in_library_none}")
print(f"\nhas source_file: {has_source_file}")

# Show some examples of in_library=False
print("\n=== Examples of in_library=False ===")
count = 0
for p in all_vf:
    meta = p.payload.get('meta', {})
    if meta.get('in_library') is False and count < 5:
        print(f"  {p.payload.get('paper_id')}: {meta.get('title', '?')[:50]}")
        count += 1
