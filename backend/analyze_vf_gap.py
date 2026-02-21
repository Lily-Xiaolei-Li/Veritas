"""
分析不在 VF Store 但有 chunks 的论文
"""
import json
from pathlib import Path

with open('data/incomplete_papers.json') as f:
    data = json.load(f)

print('=== 统计摘要 ===')
print(f"不在 VF Store: {data['stats']['not_in_vf_total']} 篇")
print(f"  - 有 DOI: {data['stats']['not_in_vf_with_doi']}")
print(f"无 Chunks: {data['stats']['no_chunks_total']} 篇")
print(f"  - 有 DOI: {data['stats']['no_chunks_with_doi']}")

# 检查不在 VF 的论文是否有对应的 chunks 文件夹
chunks_dir = Path(r'C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks')
all_chunk_folders = {f.name for f in chunks_dir.iterdir() if f.is_dir()}

print(f"\nChunks 文件夹总数: {len(all_chunk_folders)}")

print()
print('=== 分析不在 VF Store 的论文 ===')
not_in_vf = data['not_in_vf_store']

# 分类
with_chunks_prefix = []
without_chunks_prefix = []

for p in not_in_vf:
    pid = p['paper_id']
    if pid.startswith('CHUNKS_'):
        with_chunks_prefix.append(p)
    else:
        without_chunks_prefix.append(p)

print(f"以 CHUNKS_ 开头: {len(with_chunks_prefix)} 篇")
print(f"不以 CHUNKS_ 开头: {len(without_chunks_prefix)} 篇")

# 检查 CHUNKS_ 开头的是否有实际 chunks 文件夹
print()
print('=== 以 CHUNKS_ 开头的论文检查 ===')
print('这些 paper_id 暗示有 chunks 但不在 VF Store:')

sample_chunks_papers = []
for p in with_chunks_prefix[:15]:
    pid = p['paper_id']
    # 尝试匹配 chunks 文件夹
    clean_name = pid[7:] if pid.startswith('CHUNKS_') else pid
    
    # 精确匹配或部分匹配
    matches = [f for f in all_chunk_folders if clean_name[:40].lower() in f.lower()]
    
    doi_mark = "📎" if p.get('doi') else "  "
    if matches:
        sample_chunks_papers.append(p)
        print(f"  ✅ {doi_mark} {pid[:60]}")
        print(f"      -> chunks: {matches[0]}")
    else:
        print(f"  ❓ {doi_mark} {pid[:60]}")

print()
print('=' * 70)
print('📋 优先处理建议')
print('=' * 70)

# 按优先级分类
priority_1 = []  # 有 DOI + 有 chunks 文件夹 -> 只需要添加到 VF Store
priority_2 = []  # 有 DOI + 无 chunks -> 需要生成 chunks + 添加到 VF
priority_3 = []  # 无 DOI + 有 chunks -> 添加到 VF
priority_4 = []  # 无 DOI + 无 chunks -> 需要更多信息

for p in not_in_vf:
    pid = p['paper_id']
    has_doi = bool(p.get('doi'))
    has_chunks_hint = pid.startswith('CHUNKS_')
    
    if has_doi and has_chunks_hint:
        priority_1.append(p)
    elif has_doi and not has_chunks_hint:
        priority_2.append(p)
    elif not has_doi and has_chunks_hint:
        priority_3.append(p)
    else:
        priority_4.append(p)

print(f"""
🔴 Priority 1: 有 DOI + 有 chunks 提示 = {len(priority_1)} 篇
   → 只需将 chunks 导入 VF Store（最快修复）

🟠 Priority 2: 有 DOI + 无 chunks = {len(priority_2)} 篇
   → 需要先生成 chunks，再导入 VF Store

🟡 Priority 3: 无 DOI + 有 chunks 提示 = {len(priority_3)} 篇
   → 将 chunks 导入 VF Store（但缺少 DOI 元数据）

⚪ Priority 4: 无 DOI + 无 chunks = {len(priority_4)} 篇
   → 需要更多信息才能处理
""")

# 导出优先级列表
output = {
    'priority_1_doi_and_chunks': priority_1,
    'priority_2_doi_no_chunks': priority_2,
    'priority_3_no_doi_has_chunks': priority_3,
    'priority_4_no_doi_no_chunks': priority_4,
    'no_chunks_folder': data['no_chunks']
}

with open('data/priority_fix_list.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print("已导出优先级列表到: data/priority_fix_list.json")
