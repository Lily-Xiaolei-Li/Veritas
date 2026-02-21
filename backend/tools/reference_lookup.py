"""
Reference Lookup Tool
=====================

从 VF Store paper_id 查找论文的完整参考文献列表。

查询路径:
    VF Store (paper_id) → Central Database → MD 文件 → References

用法:
    from tools.reference_lookup import lookup_references, ReferenceLookup
    
    # 简单用法
    result = lookup_references("Ahrens_2006")
    print(f"找到 {result['reference_count']} 条引用")
    
    # 批量查询
    lookup = ReferenceLookup()
    for paper_id in ["Ahrens_2006", "Chua_1986"]:
        result = lookup.lookup(paper_id)
        print(f"{paper_id}: {result['reference_count']} refs")
    lookup.close()

Author: 小蕾
Created: 2026-02-19
"""

import sqlite3
import json
import re
from pathlib import Path
from typing import List, Dict, Optional

# 默认路径配置
DEFAULT_CENTRAL_DB = Path(__file__).parent.parent / "data" / "central_index.sqlite"
DEFAULT_PARSED_DIR = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")


def normalize_title(title: str) -> str:
    """
    Normalize title for matching.
    - 转小写
    - 替换特殊字符为空格
    - 合并多余空格
    """
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r'[-:;,.\'"()\[\]/\\&?!]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def extract_references_from_md(md_path: Path) -> List[str]:
    """
    从 parsed MD 文件提取 References 列表。
    
    Args:
        md_path: MD 文件路径
        
    Returns:
        引用列表（每条引用是一个字符串）
    """
    if not md_path.exists():
        return []
    
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
        return []
    
    # 提取 references 部分到文件末尾
    ref_content = content[ref_start:]
    
    # 解析每条引用
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


class ReferenceLookup:
    """
    Reference Lookup 工具类。
    
    用于从 VF Store paper_id 查找论文的完整参考文献列表。
    """
    
    def __init__(
        self, 
        central_db: Path = None, 
        parsed_dir: Path = None,
        qdrant_host: str = 'localhost',
        qdrant_port: int = 6333
    ):
        """
        初始化 ReferenceLookup。
        
        Args:
            central_db: Central Database 路径
            parsed_dir: Parsed MD 文件目录
            qdrant_host: Qdrant 服务器地址
            qdrant_port: Qdrant 服务器端口
        """
        self.central_db = central_db or DEFAULT_CENTRAL_DB
        self.parsed_dir = parsed_dir or DEFAULT_PARSED_DIR
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        
        self._conn = None
        self._client = None
    
    @property
    def conn(self):
        """获取 SQLite 连接"""
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.central_db))
        return self._conn
    
    @property
    def client(self):
        """获取 Qdrant 客户端"""
        if self._client is None:
            from qdrant_client import QdrantClient
            self._client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
        return self._client
    
    def close(self):
        """关闭连接"""
        if self._conn:
            self._conn.close()
            self._conn = None
    
    def get_paper_meta(self, paper_id: str) -> Optional[Dict]:
        """
        从 VF Store 获取论文元数据。
        
        Args:
            paper_id: VF Store paper_id
            
        Returns:
            论文元数据字典，或 None
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        points, _ = self.client.scroll(
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
    
    def get_md_filenames(self, paper_id: str) -> List[str]:
        """
        从 Central Database 获取 MD 文件名列表。
        
        Args:
            paper_id: paper_id
            
        Returns:
            MD 文件名列表
        """
        cur = self.conn.cursor()
        cur.execute("SELECT md_filenames_json FROM papers WHERE paper_id = ?", (paper_id,))
        row = cur.fetchone()
        
        if row and row[0]:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                pass
        return []
    
    def lookup(self, paper_id: str) -> Dict:
        """
        查找论文的完整参考文献列表。
        
        Args:
            paper_id: VF Store paper_id
            
        Returns:
            {
                'paper_id': str,
                'title': str,
                'year': int,
                'md_files': List[str],
                'references_found': bool,
                'reference_count': int,
                'references': List[str]
            }
        """
        result = {
            'paper_id': paper_id,
            'title': None,
            'year': None,
            'md_files': [],
            'references_found': False,
            'reference_count': 0,
            'references': []
        }
        
        # Step 1: 获取元数据
        meta = self.get_paper_meta(paper_id)
        if meta:
            result['title'] = meta.get('title')
            result['year'] = meta.get('year')
        
        # Step 2: 获取 MD 文件名
        md_files = self.get_md_filenames(paper_id)
        result['md_files'] = md_files
        
        if not md_files:
            return result
        
        # Step 3: 提取 references
        for md_file in md_files:
            md_path = self.parsed_dir / md_file
            refs = extract_references_from_md(md_path)
            
            if refs:
                result['references_found'] = True
                result['reference_count'] = len(refs)
                result['references'] = refs
                break
        
        return result


def lookup_references(paper_id: str, **kwargs) -> Dict:
    """
    便捷函数：查找论文的参考文献列表。
    
    Args:
        paper_id: VF Store paper_id
        **kwargs: 传递给 ReferenceLookup 的参数
        
    Returns:
        查找结果字典
    """
    lookup = ReferenceLookup(**kwargs)
    try:
        return lookup.lookup(paper_id)
    finally:
        lookup.close()


# 命令行接口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python reference_lookup.py <paper_id>")
        print("示例: python reference_lookup.py Ahrens_2006")
        sys.exit(1)
    
    paper_id = sys.argv[1]
    result = lookup_references(paper_id)
    
    print(f"Paper ID: {result['paper_id']}")
    print(f"Title: {result['title']}")
    print(f"Year: {result['year']}")
    print(f"MD Files: {result['md_files']}")
    print(f"References Found: {result['references_found']}")
    print(f"Reference Count: {result['reference_count']}")
    
    if result['references']:
        print("\nReferences (first 10):")
        for i, ref in enumerate(result['references'][:10], 1):
            ref_preview = ref[:100] + '...' if len(ref) > 100 else ref
            print(f"  {i}. {ref_preview}")
