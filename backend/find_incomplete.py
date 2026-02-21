"""
找出有 title/DOI 但 VF Store 数据不完整的论文
"""
import sqlite3
import json
from pathlib import Path
from collections import defaultdict

conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print("=" * 70)
print("🔍 有 Title/DOI 但数据不完整的论文分析")
print("=" * 70)

# 获取所有论文的详细信息
cur.execute("""
SELECT 
    paper_id, title, doi, year,
    in_vf_store, has_chunks_folder, 
    has_abstract, has_introduction, has_methodology, has_conclusion,
    lib_chunk_count, canonical_id, in_excel_index
FROM papers
""")

columns = [d[0] for d in cur.description]
papers = [dict(zip(columns, row)) for row in cur.fetchall()]

# 分类问题论文
issues = defaultdict(list)

for p in papers:
    has_title = p['title'] and len(p['title'].strip()) > 0
    has_doi = p['doi'] and len(p['doi'].strip()) > 0
    has_identifier = has_title or has_doi
    
    if not has_identifier:
        continue  # 跳过没有基本信息的
    
    # 检查各种不完整情况
    problems = []
    
    # 1. 不在 VF Store
    if not p['in_vf_store']:
        problems.append('not_in_vf_store')
    
    # 2. 没有 chunks 文件夹
    if not p['has_chunks_folder']:
        problems.append('no_chunks_folder')
    
    # 3. 缺少核心章节
    if p['has_chunks_folder']:  # 有 chunks 但缺章节
        if not p['has_introduction']:
            problems.append('missing_introduction')
        if not p['has_conclusion']:
            problems.append('missing_conclusion')
        if not p['has_abstract']:
            problems.append('missing_abstract')
        if not p['has_methodology']:
            problems.append('missing_methodology')
    
    # 4. chunks 数量异常少
    if p['lib_chunk_count'] and p['lib_chunk_count'] < 5:
        problems.append('few_chunks')
    
    # 5. 没有 canonical_id（难以跨系统追踪）
    if not p['canonical_id']:
        problems.append('no_canonical_id')
    
    # 记录问题
    for prob in problems:
        issues[prob].append({
            'paper_id': p['paper_id'],
            'title': p['title'][:60] + '...' if p['title'] and len(p['title']) > 60 else p['title'],
            'doi': p['doi'],
            'year': p['year'],
            'has_title': has_title,
            'has_doi': has_doi
        })

# 统计报告
print("\n📊 问题分类统计")
print("-" * 70)

priority_order = [
    ('not_in_vf_store', '不在 VF Store（无法搜索）', '🔴'),
    ('no_chunks_folder', '无 Chunks 文件夹（无法提取章节）', '🔴'),
    ('missing_introduction', '缺少 Introduction', '🟡'),
    ('missing_conclusion', '缺少 Conclusion', '🟡'),
    ('missing_abstract', '缺少 Abstract', '🟡'),
    ('missing_methodology', '缺少 Methodology', '🟠'),
    ('few_chunks', 'Chunks 过少 (<5)', '🟠'),
    ('no_canonical_id', '无 canonical_id', '⚪'),
]

for issue_type, desc, emoji in priority_order:
    count = len(issues[issue_type])
    if count > 0:
        # 统计有 DOI 的比例
        with_doi = sum(1 for p in issues[issue_type] if p['has_doi'])
        print(f"{emoji} {desc}: {count} 篇 (其中 {with_doi} 篇有 DOI)")

# 高优先级详细列表
print("\n" + "=" * 70)
print("🔴 高优先级：有 Title/DOI 但不在 VF Store")
print("=" * 70)

not_in_vf = issues['not_in_vf_store']
# 按是否有 DOI 排序（有 DOI 的优先）
not_in_vf_sorted = sorted(not_in_vf, key=lambda x: (not x['has_doi'], x['paper_id']))

print(f"\n总计: {len(not_in_vf)} 篇")
print(f"  - 有 DOI: {sum(1 for p in not_in_vf if p['has_doi'])}")
print(f"  - 仅有 Title: {sum(1 for p in not_in_vf if not p['has_doi'])}")

print("\n前 20 篇示例:")
for i, p in enumerate(not_in_vf_sorted[:20], 1):
    doi_mark = "📎" if p['has_doi'] else "  "
    print(f"  {i:2}. {doi_mark} {p['paper_id']}")
    if p['doi']:
        print(f"      DOI: {p['doi']}")

# 无 chunks 但有基本信息
print("\n" + "=" * 70)
print("🔴 高优先级：有 Title/DOI 但无 Chunks")
print("=" * 70)

no_chunks = issues['no_chunks_folder']
no_chunks_sorted = sorted(no_chunks, key=lambda x: (not x['has_doi'], x['paper_id']))

print(f"\n总计: {len(no_chunks)} 篇")
print(f"  - 有 DOI: {sum(1 for p in no_chunks if p['has_doi'])}")

print("\n前 20 篇示例:")
for i, p in enumerate(no_chunks_sorted[:20], 1):
    doi_mark = "📎" if p['has_doi'] else "  "
    year_str = f"({p['year']})" if p['year'] else ""
    print(f"  {i:2}. {doi_mark} {p['paper_id']} {year_str}")

# 交叉分析
print("\n" + "=" * 70)
print("📈 交叉分析")
print("=" * 70)

# 既不在 VF 也没有 chunks
both_missing = set(p['paper_id'] for p in issues['not_in_vf_store']) & \
               set(p['paper_id'] for p in issues['no_chunks_folder'])
print(f"\n同时不在 VF Store 且无 Chunks: {len(both_missing)} 篇")

# 在 VF Store 但缺核心章节
in_vf_but_incomplete = set()
for issue in ['missing_introduction', 'missing_conclusion']:
    for p in issues[issue]:
        pid = p['paper_id']
        if pid not in set(pp['paper_id'] for pp in issues['not_in_vf_store']):
            in_vf_but_incomplete.add(pid)
print(f"在 VF Store 但缺 intro/conclusion: {len(in_vf_but_incomplete)} 篇")

# 导出待处理列表
print("\n" + "=" * 70)
print("📤 导出待处理列表")
print("=" * 70)

output = {
    'not_in_vf_store': [{'paper_id': p['paper_id'], 'doi': p['doi'], 'title': p['title']} 
                        for p in not_in_vf_sorted],
    'no_chunks': [{'paper_id': p['paper_id'], 'doi': p['doi'], 'title': p['title']} 
                  for p in no_chunks_sorted],
    'stats': {
        'not_in_vf_total': len(not_in_vf),
        'not_in_vf_with_doi': sum(1 for p in not_in_vf if p['has_doi']),
        'no_chunks_total': len(no_chunks),
        'no_chunks_with_doi': sum(1 for p in no_chunks if p['has_doi']),
    }
}

output_path = Path('data/incomplete_papers.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"已导出到: {output_path}")

conn.close()
