"""
分析无 chunks 的论文来源
"""
import sqlite3
import json
from pathlib import Path

conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

# 获取所有无 chunks 的论文
cur.execute("""
SELECT paper_id, title, doi, year, pdf_filename, canonical_id, in_excel_index, in_vf_store
FROM papers 
WHERE has_chunks_folder = 0 OR has_chunks_folder IS NULL
""")

no_chunks = [dict(zip([d[0] for d in cur.description], row)) for row in cur.fetchall()]

print("=" * 70)
print("🔍 无 Chunks 论文分析")
print("=" * 70)
print(f"总计: {len(no_chunks)} 篇")

# 分类
has_pdf = [p for p in no_chunks if p.get('pdf_filename')]
has_doi = [p for p in no_chunks if p.get('doi')]
in_excel = [p for p in no_chunks if p.get('in_excel_index')]
in_vf = [p for p in no_chunks if p.get('in_vf_store')]

print(f"\n有 PDF 文件名: {len(has_pdf)} 篇")
print(f"有 DOI: {len(has_doi)} 篇")
print(f"在 Excel 索引: {len(in_excel)} 篇")
print(f"在 VF Store: {len(in_vf)} 篇 (但无 chunks?)")

# 检查 PDF 是否实际存在
raw_pdfs_dir = Path(r'C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\raw_pdfs')
library_dir = Path(r'C:\Users\Barry Li (UoN)\OneDrive - The University Of Newcastle\Desktop\AI\Library')

print("\n=== 检查 PDF 来源 ===")

pdf_exists = 0
pdf_in_library = 0

for p in has_pdf[:20]:
    pdf_name = p['pdf_filename']
    
    # 检查 raw_pdfs
    if (raw_pdfs_dir / pdf_name).exists():
        pdf_exists += 1
    
    # 检查 Library
    if list(library_dir.glob(f"**/{pdf_name}")):
        pdf_in_library += 1

print(f"样本检查 (前20篇有PDF的):")
print(f"  在 raw_pdfs: ~{pdf_exists}")
print(f"  在 Library: ~{pdf_in_library}")

# 分析无 chunks 但在 VF Store 的情况
print("\n=== 无 chunks 但在 VF Store ===")
print(f"总计: {len(in_vf)} 篇")
if in_vf:
    print("样本:")
    for p in in_vf[:5]:
        print(f"  - {p['paper_id']}: {p['title'][:50] if p['title'] else 'No title'}...")

# 分析来源未知的论文
unknown = [p for p in no_chunks if not p.get('doi') and not p.get('pdf_filename') and not p.get('in_excel_index')]
print(f"\n=== 来源完全未知 (无 DOI/PDF/Excel) ===")
print(f"总计: {len(unknown)} 篇")
if unknown:
    print("样本:")
    for p in unknown[:10]:
        title = p['title'][:50] + '...' if p['title'] and len(p['title']) > 50 else p['title']
        print(f"  - {p['paper_id']}: {title}")

# 分析可修复的
fixable_with_doi = [p for p in no_chunks if p.get('doi')]
fixable_in_excel = [p for p in no_chunks if p.get('in_excel_index') and not p.get('doi')]

print("\n" + "=" * 70)
print("📋 修复建议")
print("=" * 70)
print(f"""
🔴 有 DOI 但无 chunks: {len(fixable_with_doi)} 篇
   → 可以用 DOI 下载 PDF 并生成 chunks

🟠 在 Excel 但无 DOI/chunks: {len(fixable_in_excel)} 篇
   → 可以从 Excel 找到原始 PDF 信息

⚪ 来源未知: {len(unknown)} 篇
   → 可能是历史遗留数据，需要手动检查
""")

# 导出有 DOI 的待处理列表
doi_list = [{'paper_id': p['paper_id'], 'doi': p['doi'], 'title': p['title']} 
            for p in fixable_with_doi]

with open('data/no_chunks_with_doi.json', 'w', encoding='utf-8') as f:
    json.dump(doi_list, f, indent=2, ensure_ascii=False)

print(f"已导出有 DOI 待处理列表: data/no_chunks_with_doi.json ({len(doi_list)} 篇)")

conn.close()
