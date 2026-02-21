"""
测试 Section Lookup 脚本
每个章节类型测试 10 个样本
"""

import sqlite3
import random
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from tools.section_lookup import SectionLookup, AVAILABLE_SECTIONS

def main():
    print("=" * 70)
    print("Section Lookup 测试 - 每个章节类型 10 个样本")
    print("=" * 70)
    print()
    
    # 连接
    client = QdrantClient(host='localhost', port=6333)
    lookup = SectionLookup()
    
    # 获取有 chunks_folder 的 paper_ids
    conn = sqlite3.connect(str(lookup.central_db))
    cur = conn.cursor()
    cur.execute("SELECT paper_id FROM papers WHERE chunks_folder IS NOT NULL AND paper_id IS NOT NULL")
    paper_ids = [row[0] for row in cur.fetchall()]
    conn.close()
    
    print(f"有 chunks_folder 的论文: {len(paper_ids)}")
    print()
    
    # 随机抽取 50 个用于测试（每个章节测试 10 个）
    random.shuffle(paper_ids)
    test_papers = paper_ids[:50]
    
    # 测试每个章节类型
    results = {}
    
    for section in AVAILABLE_SECTIONS:
        print(f"\n{'='*70}")
        print(f"测试章节: {section.upper()}")
        print("=" * 70)
        
        success = 0
        failed = 0
        char_counts = []
        samples = []
        
        for paper_id in test_papers[:10]:
            result = lookup.lookup(paper_id, section)
            
            if result['found']:
                success += 1
                char_counts.append(result['char_count'])
                if len(samples) < 3:
                    samples.append({
                        'paper_id': paper_id,
                        'title': result['title'],
                        'char_count': result['char_count'],
                        'preview': result['content'][:200] if result['content'] else ''
                    })
            else:
                failed += 1
        
        # 用不同的 10 个论文测试下一个章节
        test_papers = test_papers[10:] + test_papers[:10]
        
        results[section] = {
            'success': success,
            'failed': failed,
            'success_rate': success / 10 * 100,
            'avg_chars': sum(char_counts) / len(char_counts) if char_counts else 0,
            'samples': samples
        }
        
        print(f"\n成功: {success}/10 ({success*10}%)")
        print(f"平均字符数: {results[section]['avg_chars']:.0f}")
        
        print("\n样本:")
        for s in samples:
            print(f"  - {s['paper_id']}: {s['char_count']} chars")
            preview = s['preview'].replace('\n', ' ')[:100]
            print(f"    \"{preview}...\"")
    
    # 汇总报告
    print("\n" + "=" * 70)
    print("汇总报告")
    print("=" * 70)
    print()
    print(f"{'章节':<20} {'成功率':<12} {'平均字符数':<12}")
    print("-" * 50)
    
    for section in AVAILABLE_SECTIONS:
        r = results[section]
        print(f"{section:<20} {r['success_rate']:.0f}%{'':<8} {r['avg_chars']:.0f}")
    
    # 总体成功率
    total_success = sum(r['success'] for r in results.values())
    total_tests = len(AVAILABLE_SECTIONS) * 10
    print("-" * 50)
    print(f"{'总体':<20} {total_success/total_tests*100:.0f}%")
    
    lookup.close()

if __name__ == "__main__":
    main()
