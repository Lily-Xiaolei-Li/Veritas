"""
检查 VF Store 的 8 piece vector 结构
"""
import requests

QDRANT_URL = "http://localhost:6333"

print("=" * 70)
print("VF Store 8 Piece Vector 结构分析")
print("=" * 70)

# 检查一个有完整 VF 数据的论文
test_paper = "Chiucchi_2022"

response = requests.post(
    f"{QDRANT_URL}/collections/vf_profiles/points/scroll",
    json={
        "filter": {"must": [{"key": "paper_id", "match": {"value": test_paper}}]},
        "limit": 20,
        "with_payload": True,
        "with_vector": False
    }
)

if response.status_code == 200:
    points = response.json().get("result", {}).get("points", [])
    print(f"\n📄 {test_paper} 的 VF 结构 ({len(points)} pieces):")
    print("-" * 70)
    
    for pt in points:
        payload = pt.get("payload", {})
        chunk_id = payload.get("chunk_id", "?")
        
        print(f"\n🔹 Piece: {chunk_id}")
        
        if chunk_id == "meta":
            meta = payload.get("meta", {})
            print(f"   内容: 论文元数据")
            print(f"   Keys: {list(meta.keys())}")
            print(f"   Title: {meta.get('title', 'N/A')[:60]}...")
        else:
            # 其他 pieces
            text = payload.get("text", "")
            print(f"   内容长度: {len(text)} chars")
            if text:
                print(f"   预览: {text[:150]}...")

# 统计有完整 VF 数据的论文数量
print("\n" + "=" * 70)
print("VF Store 完整性统计")
print("=" * 70)

# 获取所有 paper_id
response = requests.post(
    f"{QDRANT_URL}/collections/vf_profiles/points/scroll",
    json={
        "limit": 10000,
        "with_payload": ["paper_id", "chunk_id"],
        "with_vector": False
    }
)

if response.status_code == 200:
    points = response.json().get("result", {}).get("points", [])
    
    # 按 paper_id 分组统计 chunks
    paper_chunks = {}
    for pt in points:
        pid = pt.get("payload", {}).get("paper_id")
        cid = pt.get("payload", {}).get("chunk_id")
        if pid:
            if pid not in paper_chunks:
                paper_chunks[pid] = set()
            paper_chunks[pid].add(cid)
    
    print(f"\n总论文数: {len(paper_chunks)}")
    
    # 统计每篇论文有多少 pieces
    piece_counts = {}
    for pid, chunks in paper_chunks.items():
        count = len(chunks)
        piece_counts[count] = piece_counts.get(count, 0) + 1
    
    print(f"\nPieces 数量分布:")
    for count in sorted(piece_counts.keys()):
        print(f"   {count} pieces: {piece_counts[count]} 篇论文")
    
    # 检查完整 8 pieces 的论文
    complete_8 = [pid for pid, chunks in paper_chunks.items() if len(chunks) == 8]
    print(f"\n✅ 有完整 8 pieces: {len(complete_8)} 篇")
    
    # 显示 8 pieces 的组成
    if complete_8:
        sample_pid = complete_8[0]
        sample_chunks = paper_chunks[sample_pid]
        print(f"\n8 Pieces 组成 (以 {sample_pid} 为例):")
        for chunk in sorted(sample_chunks):
            print(f"   - {chunk}")
