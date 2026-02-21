from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

client = QdrantClient(host='localhost', port=6333)

# 获取 collection 信息
info = client.get_collection('vf_profiles')
print(f'=== VF Profiles Collection ===')
print(f'Total points: {info.points_count}')
print()

# 获取 meta chunks
points, _ = client.scroll(
    collection_name='vf_profiles',
    scroll_filter=Filter(must=[
        FieldCondition(key='chunk_id', match=MatchValue(value='meta'))
    ]),
    limit=10,
    with_payload=True,
    with_vectors=False
)

print(f'=== Meta Chunks (first 5) ===')
print(f'Found: {len(points)} meta chunks')
print()

# 检查 item_id 在 meta 里的情况
has_item_id = 0
no_item_id = 0

for p in points:
    payload = p.payload
    meta = payload.get('meta', {})
    if meta.get('item_id'):
        has_item_id += 1
    else:
        no_item_id += 1

print(f'Has item_id in meta: {has_item_id}/{len(points)}')
print(f'No item_id in meta: {no_item_id}/{len(points)}')
print()

# 详细看几条
print('=== Sample Records ===')
for p in points[:3]:
    payload = p.payload
    print(f"paper_id: {payload.get('paper_id')}")
    print(f"chunk_id: {payload.get('chunk_id')}")
    
    meta = payload.get('meta', {})
    print(f"meta.item_id: {meta.get('item_id', 'NOT FOUND')}")
    print(f"meta.in_library: {meta.get('in_library')}")
    print(f"meta.title: {meta.get('title', '')[:50]}...")
    print('---')

# 检查所有 meta chunks 的 item_id 情况
print()
print('=== 全量检查 item_id ===')
all_points, _ = client.scroll(
    collection_name='vf_profiles',
    scroll_filter=Filter(must=[
        FieldCondition(key='chunk_id', match=MatchValue(value='meta'))
    ]),
    limit=2000,
    with_payload=True,
    with_vectors=False
)

total = len(all_points)
with_item_id = sum(1 for p in all_points if p.payload.get('meta', {}).get('item_id'))
print(f'Total meta chunks: {total}')
print(f'With item_id: {with_item_id} ({with_item_id/total*100:.1f}%)')
print(f'Without item_id: {total - with_item_id}')

# 检查 chunk 结构
print()
print('=== VF Store Chunk 结构 ===')
sample_paper = points[0].payload.get('paper_id') if points else None
if sample_paper:
    paper_chunks, _ = client.scroll(
        collection_name='vf_profiles',
        scroll_filter=Filter(must=[
            FieldCondition(key='paper_id', match=MatchValue(value=sample_paper))
        ]),
        limit=20,
        with_payload=True,
        with_vectors=False
    )
    print(f"Paper: {sample_paper}")
    print(f"Total chunks: {len(paper_chunks)}")
    print("Chunk IDs:")
    for c in paper_chunks:
        print(f"  - {c.payload.get('chunk_id')}")
