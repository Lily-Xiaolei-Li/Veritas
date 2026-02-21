"""
全量抽样测试：VF Store → References 查询成功率
抽样 5% 的记录进行测试
"""

import sqlite3
import json
import re
import random
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

# 路径配置
CENTRAL_DB = Path(__file__).parent / "data" / "central_index.sqlite"
PARSED_DIR = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")

def extract_references_from_md(md_path: Path) -> int:
    """从 parsed MD 文件提取 References 数量"""
    if not md_path.exists():
        return 0
    
    content = md_path.read_text(encoding='utf-8')
    
    # 查找 References 部分
    patterns = [
        r'(?i)^#+\s*references?\s*$',
        r'(?i)^#+\s*bibliography\s*$',
        r'(?i)^references?\s*$',
        r'(?i)\n\s*references?\s*\n',
    ]
    
    ref_start = -1
    for pattern in patterns:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            ref_start = match.end()
            break
    
    if ref_start == -1:
        return 0
    
    # 提取 references 部分
    ref_content = content[ref_start:]
    
    # 计算引用数量（简单方法：计算以 - 或数字开头的行）
    ref_count = 0
    for line in ref_content.split('\n'):
        line = line.strip()
        if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+[\.\)]\s+', line) or re.match(r'^\[\d+\]', line):
            if len(line) > 20:
                ref_count += 1
    
    return ref_count

def main():
    print("=" * 70)
    print("全量抽样测试：VF Store → References 查询")
    print("=" * 70)
    print()
    
    # 连接
    client = QdrantClient(host='localhost', port=6333)
    conn = sqlite3.connect(str(CENTRAL_DB))
    cur = conn.cursor()
    
    # 获取所有 VF Store papers
    points, _ = client.scroll(
        collection_name='vf_profiles',
        scroll_filter=Filter(must=[
            FieldCondition(key='chunk_id', match=MatchValue(value='meta'))
        ]),
        limit=2000,
        with_payload=True,
        with_vectors=False
    )
    
    total_vf = len(points)
    print(f"VF Store 总论文数: {total_vf}")
    
    # 5% 抽样
    sample_size = max(50, int(total_vf * 0.05))
    random.shuffle(points)
    samples = points[:sample_size]
    
    print(f"抽样数量: {sample_size} ({sample_size/total_vf*100:.1f}%)")
    print()
    
    # 统计
    stats = {
        'total': sample_size,
        'has_md': 0,
        'has_refs': 0,
        'no_md': 0,
        'no_refs': 0,
        'ref_counts': [],
    }
    
    no_md_samples = []
    success_samples = []
    
    for i, p in enumerate(samples):
        paper_id = p.payload.get('paper_id')
        
        # 从 Central Database 获取 MD 文件名
        cur.execute("SELECT md_filenames_json FROM papers WHERE paper_id = ?", (paper_id,))
        row = cur.fetchone()
        
        md_files = []
        if row and row[0]:
            try:
                md_files = json.loads(row[0])
            except:
                pass
        
        if not md_files:
            stats['no_md'] += 1
            if len(no_md_samples) < 10:
                no_md_samples.append(paper_id)
            continue
        
        stats['has_md'] += 1
        
        # 检查 references
        ref_count = 0
        for md_file in md_files:
            md_path = PARSED_DIR / md_file
            ref_count = extract_references_from_md(md_path)
            if ref_count > 0:
                break
        
        if ref_count > 0:
            stats['has_refs'] += 1
            stats['ref_counts'].append(ref_count)
            if len(success_samples) < 5:
                success_samples.append((paper_id, ref_count))
        else:
            stats['no_refs'] += 1
        
        # 进度
        if (i + 1) % 20 == 0:
            print(f"  进度: {i+1}/{sample_size}")
    
    # 报告
    print()
    print("=" * 70)
    print("抽样测试结果")
    print("=" * 70)
    print()
    
    print(f"总抽样: {stats['total']}")
    print(f"有 MD 文件: {stats['has_md']} ({stats['has_md']/stats['total']*100:.1f}%)")
    print(f"无 MD 文件: {stats['no_md']} ({stats['no_md']/stats['total']*100:.1f}%)")
    print()
    
    if stats['has_md'] > 0:
        print(f"有 MD 的论文中:")
        print(f"  找到 References: {stats['has_refs']} ({stats['has_refs']/stats['has_md']*100:.1f}%)")
        print(f"  未找到 References: {stats['no_refs']} ({stats['no_refs']/stats['has_md']*100:.1f}%)")
    
    print()
    print(f"总体成功率 (VF → References): {stats['has_refs']}/{stats['total']} ({stats['has_refs']/stats['total']*100:.1f}%)")
    
    if stats['ref_counts']:
        avg_refs = sum(stats['ref_counts']) / len(stats['ref_counts'])
        print(f"平均引用数: {avg_refs:.1f}")
        print(f"最少引用数: {min(stats['ref_counts'])}")
        print(f"最多引用数: {max(stats['ref_counts'])}")
    
    print()
    print("成功样本:")
    for paper_id, ref_count in success_samples:
        print(f"  - {paper_id}: {ref_count} references")
    
    print()
    print("无 MD 文件样本:")
    for paper_id in no_md_samples[:10]:
        print(f"  - {paper_id}")
    
    conn.close()

if __name__ == "__main__":
    main()
