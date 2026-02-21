import sqlite3
import os
from pathlib import Path

CHUNKS_DIR = Path(r'C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks')

conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print('=== 分层抽样检验 (5%) ===')
print()

# 抽样
samples = {}
layers = [
    ('3源', '(in_vf_store + in_library_index + has_chunks_folder) = 3', 25),
    ('2源', '(in_vf_store + in_library_index + has_chunks_folder) = 2', 20),
    ('1源', '(in_vf_store + in_library_index + has_chunks_folder) = 1', 20),
]

total_samples = 0
for name, condition, size in layers:
    cur.execute(f'SELECT * FROM papers WHERE {condition} ORDER BY RANDOM() LIMIT {size}')
    columns = [d[0] for d in cur.description]
    rows = cur.fetchall()
    samples[name] = [dict(zip(columns, r)) for r in rows]
    print(f'{name}: 抽样 {len(samples[name])} 条')
    total_samples += len(samples[name])

print(f'总抽样: {total_samples} 条')
print()

# 检验
errors = {'critical': 0, 'major': 0, 'minor': 0}
error_details = []

for layer, records in samples.items():
    for r in records:
        # 检查 VF 链接
        if r.get('in_vf_store') and not r.get('paper_id'):
            errors['major'] += 1
            error_details.append(f"id={r['id']}: in_vf_store=1 但无 paper_id")
        
        # 检查 Library 链接
        if r.get('in_library_index') and not r.get('item_ids_json'):
            errors['minor'] += 1
        
        # 检查 Chunks 链接
        if r.get('has_chunks_folder'):
            folder = r.get('chunks_folder')
            if not folder:
                errors['major'] += 1
                error_details.append(f"id={r['id']}: has_chunks_folder=1 但无 chunks_folder")
            elif not (CHUNKS_DIR / folder).exists():
                errors['major'] += 1
                error_details.append(f"id={r['id']}: chunks_folder={folder} 不存在")
            else:
                # 检查 section 标记
                for sec in ['abstract', 'introduction', 'methodology', 'conclusion']:
                    has_sec = r.get(f'has_{sec}', 0)
                    file_exists = (CHUNKS_DIR / folder / f'{sec}.txt').exists()
                    if has_sec and not file_exists:
                        errors['minor'] += 1
                    elif not has_sec and file_exists:
                        errors['minor'] += 1
        
        # 基础完整性
        if not r.get('title'):
            errors['minor'] += 1
        
        year = r.get('year')
        if year and (year < 1980 or year > 2026):
            errors['minor'] += 1

print('=== 检验结果 ===')
print(f"Critical: {errors['critical']}")
print(f"Major: {errors['major']}")
print(f"Minor: {errors['minor']}")

for d in error_details[:10]:
    print(f'  - {d}')

print()
critical_rate = errors['critical'] / total_samples * 100
major_rate = errors['major'] / total_samples * 100
minor_rate = errors['minor'] / total_samples * 100

print('=== 错误率 ===')
print(f'Critical: {critical_rate:.1f}% (标准: 0%)')
print(f'Major: {major_rate:.1f}% (标准: <5%)')
print(f'Minor: {minor_rate:.1f}% (标准: <10%)')

print()
if errors['critical'] > 0:
    print('❌ FAIL: 存在 Critical 错误')
elif major_rate > 5:
    print('❌ FAIL: Major 错误率 > 5%')
elif minor_rate > 10:
    print('⚠️ WARNING: Minor 错误率 > 10%')
else:
    print('✅ PASS: 抽样检验通过')

conn.close()
