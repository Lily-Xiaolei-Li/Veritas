"""
Priority 1 修复计划分析

目标：将有 chunks 但不在 Qdrant 的论文导入 vf_profiles
"""
import sqlite3
import json
from pathlib import Path
import requests

QDRANT_URL = "http://localhost:6333"
chunks_dir = Path(r'C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks')

conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print("=" * 70)
print("Priority 1 修复计划分析")
print("=" * 70)

# 获取 Priority 1 论文
# 以 CHUNKS_ 开头的 paper_id 表示有 chunks 文件夹
cur.execute("""
SELECT paper_id, chunks_folder, title, doi, year, authors_json
FROM papers 
WHERE paper_id LIKE 'CHUNKS_%'
""")

priority1_papers = []
for row in cur.fetchall():
    pid, chunks_folder, title, doi, year, authors_json = row
    
    # 去掉 CHUNKS_ 前缀得到实际 chunks 文件夹名
    folder_name = pid[7:] if pid.startswith('CHUNKS_') else pid
    folder_path = chunks_dir / folder_name
    
    if folder_path.exists():
        # 检查文件夹内容
        txt_files = list(folder_path.glob('*.txt'))
        json_files = list(folder_path.glob('*.json'))
        
        priority1_papers.append({
            'paper_id': pid,
            'clean_id': folder_name,
            'chunks_folder': str(folder_path),
            'title': title,
            'doi': doi,
            'year': year,
            'txt_files': [f.stem for f in txt_files],
            'json_files': [f.name for f in json_files],
            'has_meta_json': any('meta' in f.name.lower() for f in json_files),
        })

print(f"\n找到 {len(priority1_papers)} 篇 Priority 1 论文有 chunks 文件夹")

# 分析元数据来源
has_title = sum(1 for p in priority1_papers if p['title'])
has_doi = sum(1 for p in priority1_papers if p['doi'])
has_year = sum(1 for p in priority1_papers if p['year'])
has_meta_json = sum(1 for p in priority1_papers if p['has_meta_json'])

print(f"\n📊 元数据可用性：")
print(f"   有 title (SQLite): {has_title}")
print(f"   有 DOI (SQLite): {has_doi}")
print(f"   有 year (SQLite): {has_year}")
print(f"   有 meta.json 文件: {has_meta_json}")

# 检查样本的 json 文件内容
print(f"\n📄 检查 JSON 元数据文件：")
for p in priority1_papers[:3]:
    if p['json_files']:
        json_path = Path(p['chunks_folder']) / p['json_files'][0]
        print(f"\n{p['clean_id']}:")
        print(f"   JSON files: {p['json_files']}")
        try:
            with open(json_path, encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    print(f"   Keys: {list(data.keys())[:10]}")
                else:
                    print(f"   Type: {type(data)}")
        except Exception as e:
            print(f"   Error reading: {e}")

# 修复方案
print("\n" + "=" * 70)
print("🛠️ 修复方案")
print("=" * 70)

print("""
方案 A: 最小修复 (只让 section_lookup 工作)
----------------------------------------
1. 为每篇论文创建 vf_profiles meta record:
   - paper_id: CHUNKS_xxx 或 clean_id
   - chunk_id: 'meta'
   - meta: {title, year, doi, ...}

2. 确保 SQLite papers.chunks_folder 指向正确路径

预计工作量: ~30 分钟脚本开发 + 运行


方案 B: 完整修复 (语义搜索也工作)
----------------------------------------
1. 执行方案 A
2. 将章节内容向量化并导入 academic_papers:
   - 读取 introduction.txt, conclusion.txt 等
   - 生成 embedding
   - 导入 Qdrant

预计工作量: ~1 小时脚本开发 + 运行


建议: 先执行方案 A，确保工具可用
""")

# 导出待处理列表
output = {
    'count': len(priority1_papers),
    'papers': priority1_papers[:50],  # 前50个样本
    'stats': {
        'has_title': has_title,
        'has_doi': has_doi,
        'has_year': has_year,
        'has_meta_json': has_meta_json,
    }
}

with open('data/priority1_fix_plan.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n📤 已导出修复计划: data/priority1_fix_plan.json")

conn.close()
