"""
Section Lookup Tool
===================

从 VF Store paper_id 查找论文的特定章节（introduction, methodology 等）。

基于 library-rag/data/chunks/ 中的 thematic chunks。

可用章节:
- abstract
- introduction
- methodology
- literature_review
- empirical_analysis
- conclusion

用法:
    from tools.section_lookup import lookup_section, lookup_all_sections, SectionLookup
    
    # 查找单个章节
    result = lookup_section("Ahrens_2006", "introduction")
    print(result['content'][:500])
    
    # 查找所有章节
    results = lookup_all_sections("Ahrens_2006")
    for section, data in results['sections'].items():
        print(f"{section}: {data['char_count']} chars")
    
    # 命令行
    python -m tools.section_lookup Ahrens_2006 methodology

Author: 小蕾
Created: 2026-02-19
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional

# 默认路径配置
DEFAULT_CENTRAL_DB = Path(__file__).parent.parent / "data" / "central_index.sqlite"
DEFAULT_CHUNKS_DIR = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks")

# 可用章节列表
AVAILABLE_SECTIONS = [
    'abstract',
    'introduction', 
    'methodology',
    'literature_review',
    'empirical_analysis',
    'conclusion'
]


class SectionLookup:
    """
    Section Lookup 工具类。
    
    用于从 VF Store paper_id 查找论文的特定章节。
    """
    
    def __init__(
        self, 
        central_db: Path = None, 
        chunks_dir: Path = None,
        qdrant_host: str = 'localhost',
        qdrant_port: int = 6333
    ):
        """
        初始化 SectionLookup。
        
        Args:
            central_db: Central Database 路径
            chunks_dir: Chunks 文件目录
            qdrant_host: Qdrant 服务器地址
            qdrant_port: Qdrant 服务器端口
        """
        self.central_db = central_db or DEFAULT_CENTRAL_DB
        self.chunks_dir = chunks_dir or DEFAULT_CHUNKS_DIR
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
        """从 VF Store 获取论文元数据"""
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
    
    def get_chunks_folder(self, paper_id: str) -> Optional[str]:
        """从 Central Database 获取 chunks 文件夹名"""
        cur = self.conn.cursor()
        cur.execute("SELECT chunks_folder FROM papers WHERE paper_id = ?", (paper_id,))
        row = cur.fetchone()
        
        if row and row[0]:
            return row[0]
        return None
    
    def read_section(self, chunks_folder: str, section: str) -> Optional[str]:
        """
        读取指定章节的内容。
        
        Args:
            chunks_folder: chunks 文件夹名
            section: 章节名 (abstract, introduction, etc.)
            
        Returns:
            章节内容，或 None
        """
        section_file = self.chunks_dir / chunks_folder / f"{section}.txt"
        
        if section_file.exists():
            return section_file.read_text(encoding='utf-8')
        return None
    
    def lookup(self, paper_id: str, section: str) -> Dict:
        """
        查找论文的指定章节。
        
        Args:
            paper_id: VF Store paper_id
            section: 章节名
            
        Returns:
            {
                'paper_id': str,
                'title': str,
                'year': int,
                'section': str,
                'chunks_folder': str,
                'found': bool,
                'content': str,
                'char_count': int
            }
        """
        if section not in AVAILABLE_SECTIONS:
            raise ValueError(f"Invalid section: {section}. Available: {AVAILABLE_SECTIONS}")
        
        result = {
            'paper_id': paper_id,
            'title': None,
            'year': None,
            'section': section,
            'chunks_folder': None,
            'found': False,
            'content': None,
            'char_count': 0
        }
        
        # 获取元数据
        meta = self.get_paper_meta(paper_id)
        if meta:
            result['title'] = meta.get('title')
            result['year'] = meta.get('year')
        
        # 获取 chunks 文件夹
        chunks_folder = self.get_chunks_folder(paper_id)
        result['chunks_folder'] = chunks_folder
        
        if not chunks_folder:
            return result
        
        # 读取章节内容
        content = self.read_section(chunks_folder, section)
        
        if content:
            result['found'] = True
            result['content'] = content
            result['char_count'] = len(content)
        
        return result
    
    def lookup_all(self, paper_id: str) -> Dict:
        """
        查找论文的所有可用章节。
        
        Args:
            paper_id: VF Store paper_id
            
        Returns:
            {
                'paper_id': str,
                'title': str,
                'year': int,
                'chunks_folder': str,
                'sections': {
                    'abstract': {'found': bool, 'content': str, 'char_count': int},
                    'introduction': {...},
                    ...
                },
                'sections_found': int,
                'total_chars': int
            }
        """
        result = {
            'paper_id': paper_id,
            'title': None,
            'year': None,
            'chunks_folder': None,
            'sections': {},
            'sections_found': 0,
            'total_chars': 0
        }
        
        # 获取元数据
        meta = self.get_paper_meta(paper_id)
        if meta:
            result['title'] = meta.get('title')
            result['year'] = meta.get('year')
        
        # 获取 chunks 文件夹
        chunks_folder = self.get_chunks_folder(paper_id)
        result['chunks_folder'] = chunks_folder
        
        if not chunks_folder:
            for section in AVAILABLE_SECTIONS:
                result['sections'][section] = {'found': False, 'content': None, 'char_count': 0}
            return result
        
        # 读取所有章节
        for section in AVAILABLE_SECTIONS:
            content = self.read_section(chunks_folder, section)
            
            if content:
                result['sections'][section] = {
                    'found': True,
                    'content': content,
                    'char_count': len(content)
                }
                result['sections_found'] += 1
                result['total_chars'] += len(content)
            else:
                result['sections'][section] = {
                    'found': False,
                    'content': None,
                    'char_count': 0
                }
        
        return result


def lookup_section(paper_id: str, section: str, **kwargs) -> Dict:
    """
    便捷函数：查找论文的指定章节。
    
    Args:
        paper_id: VF Store paper_id
        section: 章节名 (abstract, introduction, methodology, 
                 literature_review, empirical_analysis, conclusion)
        **kwargs: 传递给 SectionLookup 的参数
        
    Returns:
        查找结果字典
    """
    lookup = SectionLookup(**kwargs)
    try:
        return lookup.lookup(paper_id, section)
    finally:
        lookup.close()


def lookup_all_sections(paper_id: str, **kwargs) -> Dict:
    """
    便捷函数：查找论文的所有章节。
    
    Args:
        paper_id: VF Store paper_id
        **kwargs: 传递给 SectionLookup 的参数
        
    Returns:
        查找结果字典
    """
    lookup = SectionLookup(**kwargs)
    try:
        return lookup.lookup_all(paper_id)
    finally:
        lookup.close()


# 便捷函数：按章节名快速查找
def lookup_abstract(paper_id: str, **kwargs) -> Dict:
    """查找论文摘要"""
    return lookup_section(paper_id, 'abstract', **kwargs)

def lookup_introduction(paper_id: str, **kwargs) -> Dict:
    """查找论文引言"""
    return lookup_section(paper_id, 'introduction', **kwargs)

def lookup_methodology(paper_id: str, **kwargs) -> Dict:
    """查找论文方法论"""
    return lookup_section(paper_id, 'methodology', **kwargs)

def lookup_literature_review(paper_id: str, **kwargs) -> Dict:
    """查找论文文献综述"""
    return lookup_section(paper_id, 'literature_review', **kwargs)

def lookup_empirical_analysis(paper_id: str, **kwargs) -> Dict:
    """查找论文实证分析"""
    return lookup_section(paper_id, 'empirical_analysis', **kwargs)

def lookup_conclusion(paper_id: str, **kwargs) -> Dict:
    """查找论文结论"""
    return lookup_section(paper_id, 'conclusion', **kwargs)


# 命令行接口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python section_lookup.py <paper_id> [section]")
        print("示例: python section_lookup.py Ahrens_2006 introduction")
        print(f"可用章节: {', '.join(AVAILABLE_SECTIONS)}")
        print("不指定 section 则显示所有章节概览")
        sys.exit(1)
    
    paper_id = sys.argv[1]
    
    if len(sys.argv) >= 3:
        # 查找指定章节
        section = sys.argv[2]
        result = lookup_section(paper_id, section)
        
        print(f"Paper ID: {result['paper_id']}")
        print(f"Title: {result['title']}")
        print(f"Year: {result['year']}")
        print(f"Section: {result['section']}")
        print(f"Found: {result['found']}")
        print(f"Char Count: {result['char_count']}")
        
        if result['content']:
            print(f"\nContent (first 1000 chars):")
            print("-" * 50)
            print(result['content'][:1000])
            if len(result['content']) > 1000:
                print("...")
    else:
        # 查找所有章节
        result = lookup_all_sections(paper_id)
        
        print(f"Paper ID: {result['paper_id']}")
        print(f"Title: {result['title']}")
        print(f"Year: {result['year']}")
        print(f"Chunks Folder: {result['chunks_folder']}")
        print(f"Sections Found: {result['sections_found']}/{len(AVAILABLE_SECTIONS)}")
        print(f"Total Chars: {result['total_chars']}")
        print()
        print("Sections:")
        for section, data in result['sections'].items():
            status = "✅" if data['found'] else "❌"
            chars = f"{data['char_count']:,} chars" if data['found'] else "-"
            print(f"  {status} {section}: {chars}")
