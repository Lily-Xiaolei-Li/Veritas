"""
分析 chunks 文件夹的内部结构
"""
from pathlib import Path
from collections import defaultdict

chunks_dir = Path(r'C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks')

print("=" * 70)
print("Chunks 文件夹结构分析")
print("=" * 70)

# 统计
stats = {
    'total': 0,
    'empty': 0,
    'has_txt': 0,
    'has_md': 0,
    'has_json': 0,
}

file_patterns = defaultdict(int)
section_files = defaultdict(int)

for folder in chunks_dir.iterdir():
    if not folder.is_dir():
        continue
    
    stats['total'] += 1
    
    files = list(folder.iterdir())
    if not files:
        stats['empty'] += 1
        continue
    
    for f in files:
        ext = f.suffix.lower()
        file_patterns[ext] += 1
        
        # 检查是否是章节文件
        name = f.stem.lower()
        if name in ['abstract', 'introduction', 'methodology', 'conclusion', 
                    'literature_review', 'empirical_analysis', 'references']:
            section_files[name] += 1
        
        if ext == '.txt':
            stats['has_txt'] += 1
        elif ext == '.md':
            stats['has_md'] += 1
        elif ext == '.json':
            stats['has_json'] += 1

# 去重（每个文件夹只计一次）
folders_with_txt = 0
folders_with_md = 0

for folder in chunks_dir.iterdir():
    if not folder.is_dir():
        continue
    
    files = list(folder.iterdir())
    exts = {f.suffix.lower() for f in files}
    
    if '.txt' in exts:
        folders_with_txt += 1
    if '.md' in exts:
        folders_with_md += 1

print(f"\n📁 文件夹统计:")
print(f"   总文件夹: {stats['total']}")
print(f"   空文件夹: {stats['empty']}")
print(f"   有 .txt 文件的文件夹: {folders_with_txt}")
print(f"   有 .md 文件的文件夹: {folders_with_md}")

print(f"\n📄 文件扩展名分布:")
for ext, count in sorted(file_patterns.items(), key=lambda x: -x[1]):
    print(f"   {ext or '(无扩展名)'}: {count}")

print(f"\n📑 章节文件统计:")
for section, count in sorted(section_files.items(), key=lambda x: -x[1]):
    print(f"   {section}: {count} 个文件夹有此章节")

# 样本：有 txt 文件的文件夹
print("\n" + "=" * 70)
print("样本：有 .txt 章节文件的文件夹")
print("=" * 70)

count = 0
for folder in chunks_dir.iterdir():
    if not folder.is_dir():
        continue
    
    txt_files = list(folder.glob('*.txt'))
    if txt_files and count < 5:
        print(f"\n{folder.name}:")
        for f in txt_files:
            size = f.stat().st_size
            print(f"   {f.name} ({size:,} bytes)")
        count += 1

# 样本：有 md 文件的文件夹
print("\n" + "=" * 70)
print("样本：有 .md 文件的文件夹")
print("=" * 70)

count = 0
for folder in chunks_dir.iterdir():
    if not folder.is_dir():
        continue
    
    md_files = list(folder.glob('*.md'))
    if md_files and count < 5:
        print(f"\n{folder.name}:")
        for f in list(md_files)[:5]:
            size = f.stat().st_size
            print(f"   {f.name} ({size:,} bytes)")
        if len(md_files) > 5:
            print(f"   ... 还有 {len(md_files) - 5} 个文件")
        count += 1
