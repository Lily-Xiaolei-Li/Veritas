"""
Central Database 抽样检验脚本
- 5% 分层抽样
- 检验数据完整性和链接正确性
"""

import sqlite3
import random
import json
import os
from pathlib import Path

# 路径配置
CENTRAL_DB = Path(__file__).parent / "data" / "central_index.sqlite"
LIBRARY_DB = Path(__file__).parent / "data" / "library_index.sqlite"
VF_DB = Path(__file__).parent / "data" / "vf_metadata.sqlite"
CHUNKS_DIR = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks")

def sense_check(conn):
    """基础 sense check"""
    cur = conn.cursor()
    
    print("=" * 60)
    print("SENSE CHECK")
    print("=" * 60)
    
    # 总记录数
    cur.execute("SELECT COUNT(*) FROM papers")
    total = cur.fetchone()[0]
    print(f"总记录数: {total}")
    
    if total > 1500:
        print("❌ FAIL: 总记录数 > 1500，不合理！")
        return False
    else:
        print("✅ PASS: 总记录数合理")
    
    # 重复 title
    cur.execute("""
        SELECT COUNT(*) FROM (
            SELECT title FROM papers 
            WHERE title IS NOT NULL 
            GROUP BY title HAVING COUNT(*) > 1
        )
    """)
    dup_titles = cur.fetchone()[0]
    print(f"重复 title 数量: {dup_titles}")
    
    if dup_titles > 50:
        print("❌ FAIL: 重复 title > 50，匹配有问题！")
        return False
    else:
        print("✅ PASS: 重复 title 数量合理")
    
    # 多源匹配
    cur.execute("""
        SELECT COUNT(*) FROM papers 
        WHERE (in_vf_store + in_library_index + in_excel_index + has_chunks_folder) >= 2
    """)
    multi_source = cur.fetchone()[0]
    print(f"多源匹配 (>=2): {multi_source}")
    
    if multi_source < 300:
        print("⚠️ WARNING: 多源匹配 < 300，可能匹配不足")
    else:
        print("✅ PASS: 多源匹配数量合理")
    
    # 各来源覆盖
    for col in ['in_vf_store', 'in_library_index', 'in_excel_index', 'has_chunks_folder']:
        cur.execute(f"SELECT COUNT(*) FROM papers WHERE {col} = 1")
        count = cur.fetchone()[0]
        print(f"  {col}: {count}")
    
    print()
    return True

def get_stratified_samples(conn, sample_sizes):
    """分层抽样"""
    cur = conn.cursor()
    samples = {}
    
    for layer, (condition, size) in sample_sizes.items():
        cur.execute(f"""
            SELECT * FROM papers 
            WHERE {condition}
            ORDER BY RANDOM()
            LIMIT {size}
        """)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        samples[layer] = [dict(zip(columns, row)) for row in rows]
        print(f"抽样 {layer}: {len(samples[layer])} 条")
    
    return samples

def check_vf_link(record, errors, vf_conn):
    """检验 VF Store 链接"""
    if not record.get('in_vf_store'):
        return
    
    vf_paper_id = record.get('vf_paper_id')
    if not vf_paper_id:
        errors['major'].append({
            'id': record['id'],
            'type': 'vf_link',
            'msg': 'in_vf_store=1 但 vf_paper_id 为空'
        })
        return
    
    # 检查 VF SQLite 是否有此记录
    cur = vf_conn.cursor()
    cur.execute("SELECT title, year FROM vf_profiles_index WHERE paper_id = ?", (vf_paper_id,))
    vf_record = cur.fetchone()
    
    if not vf_record:
        errors['major'].append({
            'id': record['id'],
            'type': 'vf_link',
            'msg': f'vf_paper_id={vf_paper_id} 在 VF SQLite 中找不到'
        })

def check_library_link(record, errors, lib_conn):
    """检验 Library Index 链接"""
    if not record.get('in_library_index'):
        return
    
    item_id = record.get('item_id')
    if not item_id:
        errors['minor'].append({
            'id': record['id'],
            'type': 'lib_link',
            'msg': 'in_library_index=1 但 item_id 为空'
        })
        return
    
    # 检查 Library SQLite 是否有此记录
    cur = lib_conn.cursor()
    cur.execute("SELECT md_filename FROM library_index WHERE item_id = ?", (item_id,))
    lib_record = cur.fetchone()
    
    if not lib_record:
        errors['major'].append({
            'id': record['id'],
            'type': 'lib_link',
            'msg': f'item_id={item_id} 在 Library SQLite 中找不到'
        })

def check_chunks_link(record, errors):
    """检验 Chunks 文件夹链接"""
    if not record.get('has_chunks_folder'):
        return
    
    chunks_folder = record.get('chunks_folder')
    if not chunks_folder:
        errors['major'].append({
            'id': record['id'],
            'type': 'chunks_link',
            'msg': 'has_chunks_folder=1 但 chunks_folder 为空'
        })
        return
    
    # 检查文件夹是否存在
    folder_path = CHUNKS_DIR / chunks_folder
    if not folder_path.exists():
        errors['major'].append({
            'id': record['id'],
            'type': 'chunks_link',
            'msg': f'chunks_folder={chunks_folder} 不存在'
        })
        return
    
    # 检查 section 标记是否正确
    sections = ['abstract', 'introduction', 'methodology', 
                'literature_review', 'empirical_analysis', 'conclusion']
    
    for sec in sections:
        has_sec = record.get(f'has_{sec}', 0)
        file_exists = (folder_path / f'{sec}.txt').exists()
        
        if has_sec and not file_exists:
            errors['minor'].append({
                'id': record['id'],
                'type': 'section_mismatch',
                'msg': f'has_{sec}=1 但文件不存在'
            })
        elif not has_sec and file_exists:
            errors['minor'].append({
                'id': record['id'],
                'type': 'section_mismatch',
                'msg': f'has_{sec}=0 但文件存在'
            })

def check_basic_integrity(record, errors):
    """基础完整性检验"""
    # title 不应为空
    if not record.get('title'):
        errors['minor'].append({
            'id': record['id'],
            'type': 'integrity',
            'msg': 'title 为空'
        })
    
    # year 应该合理
    year = record.get('year')
    if year and (year < 1980 or year > 2026):
        errors['minor'].append({
            'id': record['id'],
            'type': 'integrity',
            'msg': f'year={year} 不合理'
        })

def run_sample_test():
    """主测试函数"""
    print("=" * 60)
    print("CENTRAL DATABASE 抽样检验")
    print("=" * 60)
    print()
    
    # 连接数据库
    if not CENTRAL_DB.exists():
        print("❌ central_index.sqlite 不存在！")
        return
    
    conn = sqlite3.connect(CENTRAL_DB)
    
    # 1. Sense Check
    if not sense_check(conn):
        print("\n❌ Sense Check 失败，停止抽样检验")
        conn.close()
        return
    
    print()
    print("=" * 60)
    print("分层抽样检验")
    print("=" * 60)
    
    # 2. 计算来源数
    cur = conn.cursor()
    cur.execute("""
        SELECT id, 
               (in_vf_store + in_library_index + in_excel_index + has_chunks_folder) as source_count
        FROM papers
    """)
    
    # 统计各层数量
    cur.execute("""
        SELECT 
            (in_vf_store + in_library_index + in_excel_index + has_chunks_folder) as sc,
            COUNT(*)
        FROM papers GROUP BY sc ORDER BY sc DESC
    """)
    print("\n各层分布:")
    for row in cur.fetchall():
        print(f"  {row[0]}源: {row[1]} 条")
    
    # 3. 分层抽样
    sample_sizes = {
        '4源': ("(in_vf_store + in_library_index + in_excel_index + has_chunks_folder) = 4", 10),
        '3源': ("(in_vf_store + in_library_index + in_excel_index + has_chunks_folder) = 3", 15),
        '2源': ("(in_vf_store + in_library_index + in_excel_index + has_chunks_folder) = 2", 20),
        '1源': ("(in_vf_store + in_library_index + in_excel_index + has_chunks_folder) = 1", 15),
    }
    
    print()
    samples = get_stratified_samples(conn, sample_sizes)
    total_samples = sum(len(s) for s in samples.values())
    print(f"\n总抽样: {total_samples} 条")
    
    # 4. 连接其他数据库
    lib_conn = sqlite3.connect(LIBRARY_DB) if LIBRARY_DB.exists() else None
    vf_conn = sqlite3.connect(VF_DB) if VF_DB.exists() else None
    
    # 5. 执行检验
    errors = {'critical': [], 'major': [], 'minor': []}
    
    for layer, records in samples.items():
        for record in records:
            check_basic_integrity(record, errors)
            if vf_conn:
                check_vf_link(record, errors, vf_conn)
            if lib_conn:
                check_library_link(record, errors, lib_conn)
            check_chunks_link(record, errors)
    
    # 6. 生成报告
    print()
    print("=" * 60)
    print("检验结果")
    print("=" * 60)
    
    print(f"\nCritical 错误: {len(errors['critical'])}")
    for e in errors['critical'][:5]:
        print(f"  - id={e['id']}: {e['msg']}")
    
    print(f"\nMajor 错误: {len(errors['major'])}")
    for e in errors['major'][:10]:
        print(f"  - id={e['id']}: {e['msg']}")
    
    print(f"\nMinor 错误: {len(errors['minor'])}")
    for e in errors['minor'][:10]:
        print(f"  - id={e['id']}: {e['msg']}")
    
    # 7. 计算错误率
    print()
    print("=" * 60)
    print("错误率统计")
    print("=" * 60)
    
    critical_rate = len(errors['critical']) / total_samples * 100
    major_rate = len(errors['major']) / total_samples * 100
    minor_rate = len(errors['minor']) / total_samples * 100
    
    print(f"Critical 错误率: {critical_rate:.1f}% (标准: 0%)")
    print(f"Major 错误率: {major_rate:.1f}% (标准: <5%)")
    print(f"Minor 错误率: {minor_rate:.1f}% (标准: <10%)")
    
    # 8. 判定结果
    print()
    if len(errors['critical']) > 0:
        print("❌ FAIL: 存在 Critical 错误")
    elif major_rate > 5:
        print("❌ FAIL: Major 错误率 > 5%")
    elif minor_rate > 10:
        print("⚠️ WARNING: Minor 错误率 > 10%")
    else:
        print("✅ PASS: 抽样检验通过")
    
    # 清理
    conn.close()
    if lib_conn:
        lib_conn.close()
    if vf_conn:
        vf_conn.close()

if __name__ == "__main__":
    run_sample_test()
