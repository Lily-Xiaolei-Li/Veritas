"""
从 VF Store 查找论文的完整参考文献列表

查询路径:
1. VF Store paper_id → Central Database (通过 paper_id 匹配)
2. Central Database → md_filenames_json → parsed MD 文件路径
3. 读取 parsed MD 文件 → 提取 References 部分
"""

import sqlite3
import json
import re
from pathlib import Path
from qdrant_client import QdrantClient

# 路径配置
CENTRAL_DB = Path(__file__).parent / "data" / "central_index.sqlite"
PARSED_DIR = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")

def get_paper_from_vf_store(paper_id: str, client: QdrantClient) -> dict:
    """从 VF Store 获取论文基本信息"""
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    points, _ = client.scroll(
        collection_name='vf_profiles',
        scroll_filter=Filter(must=[
            FieldCondition(key='paper_id', match=MatchValue(value=paper_id)),
            FieldCondition(key='chunk_id', match=MatchValue(value='meta'))
        ]),
        limit=1,
        with_payload=True,
        with_vectors=False
    )
    
    if points:
        return points[0].payload.get('meta', {})
    return None

def get_md_filename_from_central_db(paper_id: str, conn) -> list:
    """从 Central Database 获取 MD 文件名"""
    cur = conn.cursor()
    cur.execute("SELECT md_filenames_json FROM papers WHERE paper_id = ?", (paper_id,))
    row = cur.fetchone()
    
    if row and row[0]:
        try:
            return json.loads(row[0])
        except:
            pass
    return []

def extract_references_from_md(md_path: Path) -> list:
    """从 parsed MD 文件提取 References 部分"""
    if not md_path.exists():
        return []
    
    content = md_path.read_text(encoding='utf-8')
    
    # 查找 References 部分（通常在文件末尾）
    # 常见标题: References, Bibliography, Reference List, Works Cited
    patterns = [
        r'(?i)^#+\s*references?\s*$',
        r'(?i)^#+\s*bibliography\s*$',
        r'(?i)^references?\s*$',
    ]
    
    ref_start = -1
    for pattern in patterns:
        match = re.search(pattern, content, re.MULTILINE)
        if match:
            ref_start = match.end()
            break
    
    if ref_start == -1:
        # 尝试查找 "References" 关键词
        match = re.search(r'(?i)\n\s*references?\s*\n', content)
        if match:
            ref_start = match.end()
    
    if ref_start == -1:
        return []
    
    # 提取 references 部分到文件末尾
    ref_content = content[ref_start:]
    
    # 解析每条引用（通常以 - 或数字开头，或者每行一条）
    references = []
    lines = ref_content.split('\n')
    current_ref = []
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_ref:
                references.append(' '.join(current_ref))
                current_ref = []
            continue
        
        # 检测新引用的开始
        if re.match(r'^[-•*]\s+', line) or re.match(r'^\d+[\.\)]\s+', line) or re.match(r'^\[\d+\]', line):
            if current_ref:
                references.append(' '.join(current_ref))
            current_ref = [re.sub(r'^[-•*\d\.\)\[\]]+\s*', '', line)]
        else:
            current_ref.append(line)
    
    if current_ref:
        references.append(' '.join(current_ref))
    
    # 过滤太短的条目
    references = [r for r in references if len(r) > 20]
    
    return references

def lookup_references(paper_id: str, client: QdrantClient, conn) -> dict:
    """完整的引用查找流程"""
    result = {
        'paper_id': paper_id,
        'title': None,
        'year': None,
        'md_files': [],
        'references_found': False,
        'reference_count': 0,
        'sample_references': []
    }
    
    # Step 1: 从 VF Store 获取基本信息
    meta = get_paper_from_vf_store(paper_id, client)
    if meta:
        result['title'] = meta.get('title')
        result['year'] = meta.get('year')
    
    # Step 2: 从 Central Database 获取 MD 文件名
    md_files = get_md_filename_from_central_db(paper_id, conn)
    result['md_files'] = md_files
    
    if not md_files:
        return result
    
    # Step 3: 读取 MD 文件，提取 references
    for md_file in md_files:
        md_path = PARSED_DIR / md_file
        refs = extract_references_from_md(md_path)
        
        if refs:
            result['references_found'] = True
            result['reference_count'] = len(refs)
            result['sample_references'] = refs[:5]  # 只显示前5条
            break
    
    return result

def main():
    print("=" * 70)
    print("VF Store → Central DB → References 查询测试")
    print("=" * 70)
    print()
    
    # 连接
    client = QdrantClient(host='localhost', port=6333)
    conn = sqlite3.connect(str(CENTRAL_DB))
    
    # 获取 10 个 VF Store paper_id 进行测试
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    points, _ = client.scroll(
        collection_name='vf_profiles',
        scroll_filter=Filter(must=[
            FieldCondition(key='chunk_id', match=MatchValue(value='meta'))
        ]),
        limit=50,
        with_payload=True,
        with_vectors=False
    )
    
    # 随机选择 10 个
    import random
    random.shuffle(points)
    test_points = points[:10]
    
    success_count = 0
    
    for i, p in enumerate(test_points, 1):
        paper_id = p.payload.get('paper_id')
        print(f"\n--- Test {i}: {paper_id} ---")
        
        result = lookup_references(paper_id, client, conn)
        
        print(f"Title: {result['title'][:60] if result['title'] else 'N/A'}...")
        print(f"Year: {result['year']}")
        print(f"MD files: {result['md_files']}")
        print(f"References found: {result['references_found']}")
        
        if result['references_found']:
            success_count += 1
            print(f"Reference count: {result['reference_count']}")
            print("Sample references:")
            for ref in result['sample_references'][:3]:
                ref_preview = ref[:100] + '...' if len(ref) > 100 else ref
                print(f"  - {ref_preview}")
        else:
            print("  (No references found - may not have MD file or references section)")
    
    print()
    print("=" * 70)
    print(f"成功率: {success_count}/10 ({success_count*10}%)")
    print("=" * 70)
    
    conn.close()

if __name__ == "__main__":
    main()
