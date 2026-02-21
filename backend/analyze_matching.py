"""
分析 Priority 1 论文的 paper_id 和 chunks 文件夹的匹配关系
"""
import sqlite3
from pathlib import Path

chunks_dir = Path(r'C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks')
all_chunk_folders = {f.name: f for f in chunks_dir.iterdir() if f.is_dir()}

print(f"Chunks 文件夹总数: {len(all_chunk_folders)}")

conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

# 获取 Priority 1 论文 (以 CHUNKS_ 开头的 paper_id)
cur.execute("""
SELECT paper_id, chunks_folder, title, doi 
FROM papers 
WHERE paper_id LIKE 'CHUNKS_%'
LIMIT 15
""")

print("\n" + "=" * 70)
print("Priority 1 论文的 paper_id vs chunks_folder 映射")
print("=" * 70)

matched = 0
not_matched = 0

for row in cur.fetchall():
    pid, chunks_folder, title, doi = row
    
    # 去掉 CHUNKS_ 前缀
    clean_name = pid[7:] if pid.startswith('CHUNKS_') else pid
    
    print(f"\npaper_id: {pid[:60]}...")
    
    # 尝试精确匹配
    if clean_name in all_chunk_folders:
        folder = all_chunk_folders[clean_name]
        files = list(folder.glob('*.md'))
        print(f"  ✅ 精确匹配: {clean_name}")
        print(f"     MD 文件数: {len(files)}")
        if files:
            print(f"     样本文件: {files[0].name}")
        matched += 1
    else:
        # 部分匹配
        matches = [f for f in all_chunk_folders if clean_name[:40] in f]
        if matches:
            print(f"  🟡 部分匹配: {matches[0]}")
            matched += 1
        else:
            print(f"  ❌ 未找到匹配")
            not_matched += 1

print("\n" + "=" * 70)
print(f"匹配统计: {matched} 成功, {not_matched} 失败")
print("=" * 70)

# 检查一个 chunks 文件夹的内部结构
print("\n" + "=" * 70)
print("Chunks 文件夹内部结构示例")
print("=" * 70)

sample_folder = list(all_chunk_folders.values())[0]
print(f"\n文件夹: {sample_folder.name}")
files = list(sample_folder.glob('*'))
for f in files[:10]:
    print(f"  {f.name} ({f.stat().st_size} bytes)")

# 读取一个 chunk 文件看看格式
md_files = list(sample_folder.glob('*.md'))
if md_files:
    print(f"\n--- 样本 chunk 内容 ({md_files[0].name}) ---")
    content = md_files[0].read_text(encoding='utf-8')[:500]
    print(content)

conn.close()
