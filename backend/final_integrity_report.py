"""
最终数据完整性报告
"""
import requests
import sqlite3
from collections import defaultdict

QDRANT_URL = "http://localhost:6333"

conn = sqlite3.connect('data/central_index.sqlite')
cur = conn.cursor()

print("=" * 70)
print("📋 最终数据完整性报告")
print("=" * 70)

# 1. SQLite 总数
cur.execute("SELECT COUNT(*) FROM papers")
total = cur.fetchone()[0]
print(f"\n📚 SQLite 论文总数: {total}")

# 2. 获取 Qdrant 实际数据
response = requests.post(
    f"{QDRANT_URL}/collections/vf_profiles/points/scroll",
    json={"limit": 10000, "with_payload": ["paper_id"], "with_vector": False}
)
qdrant_vf_ids = set()
if response.status_code == 200:
    for p in response.json().get("result", {}).get("points", []):
        pid = p.get("payload", {}).get("paper_id")
        if pid:
            qdrant_vf_ids.add(pid)

print(f"🗄️ Qdrant vf_profiles: {len(qdrant_vf_ids)} 篇")

# 3. 获取 SQLite 所有论文
cur.execute("""
SELECT paper_id, title, doi, in_vf_store, has_chunks_folder,
       has_abstract, has_introduction, has_methodology, has_conclusion
FROM papers
""")
papers = {r[0]: {
    'title': r[1], 'doi': r[2], 'in_vf_store': r[3], 
    'has_chunks': r[4], 'has_abstract': r[5], 'has_intro': r[6],
    'has_method': r[7], 'has_conclusion': r[8]
} for r in cur.fetchall()}

# 4. 分类统计
categories = {
    'complete': [],          # 完整：在 Qdrant + 有 chunks + 有核心章节
    'in_qdrant_no_chunks': [],  # 在 Qdrant 但无 chunks
    'has_chunks_not_qdrant': [],  # 有 chunks 但不在 Qdrant
    'nothing': [],           # 既不在 Qdrant 也无 chunks
}

for pid, info in papers.items():
    in_qdrant = pid in qdrant_vf_ids
    has_chunks = info['has_chunks']
    
    if in_qdrant and has_chunks:
        categories['complete'].append({'paper_id': pid, **info})
    elif in_qdrant and not has_chunks:
        categories['in_qdrant_no_chunks'].append({'paper_id': pid, **info})
    elif not in_qdrant and has_chunks:
        categories['has_chunks_not_qdrant'].append({'paper_id': pid, **info})
    else:
        categories['nothing'].append({'paper_id': pid, **info})

print(f"\n📊 数据分类:")
print(f"  ✅ 完整 (Qdrant + chunks): {len(categories['complete'])} 篇")
print(f"  🟠 在 Qdrant 无 chunks: {len(categories['in_qdrant_no_chunks'])} 篇")
print(f"  🔴 有 chunks 不在 Qdrant: {len(categories['has_chunks_not_qdrant'])} 篇")
print(f"  ⚫ 无数据: {len(categories['nothing'])} 篇")

# 5. 详细分析有 title/DOI 的情况
print("\n" + "=" * 70)
print("🎯 优先处理：有 Title/DOI 但数据不完整")
print("=" * 70)

# 有 chunks 但不在 Qdrant
priority_1 = [p for p in categories['has_chunks_not_qdrant'] if p['title'] or p['doi']]
priority_1_doi = [p for p in priority_1 if p['doi']]
print(f"\n🔴 Priority 1: 有 chunks 但不在 Qdrant VF Store")
print(f"   总计: {len(priority_1)} 篇 (其中 {len(priority_1_doi)} 有 DOI)")
print(f"   → 需要将 chunks 导入 VF Store")

# 无数据但有 title/DOI
priority_2 = [p for p in categories['nothing'] if p['title'] or p['doi']]
priority_2_doi = [p for p in priority_2 if p['doi']]
print(f"\n🟠 Priority 2: 无 chunks 也不在 Qdrant")
print(f"   总计: {len(priority_2)} 篇 (其中 {len(priority_2_doi)} 有 DOI)")
print(f"   → 需要生成 chunks + 导入 VF Store")

# 在 Qdrant 但无 chunks
priority_3 = [p for p in categories['in_qdrant_no_chunks'] if p['title'] or p['doi']]
print(f"\n🟡 Priority 3: 在 Qdrant 但无 chunks 文件夹")
print(f"   总计: {len(priority_3)} 篇")
print(f"   → 可能是 VF 直接导入的，章节工具可能无法使用")

# 6. 章节覆盖分析
print("\n" + "=" * 70)
print("📑 章节覆盖率 (仅完整数据)")
print("=" * 70)

complete_papers = categories['complete']
if complete_papers:
    has_intro = sum(1 for p in complete_papers if p['has_intro'])
    has_concl = sum(1 for p in complete_papers if p['has_conclusion'])
    has_abstract = sum(1 for p in complete_papers if p['has_abstract'])
    has_method = sum(1 for p in complete_papers if p['has_method'])
    
    total_complete = len(complete_papers)
    print(f"  Introduction: {has_intro}/{total_complete} ({100*has_intro/total_complete:.1f}%)")
    print(f"  Conclusion: {has_concl}/{total_complete} ({100*has_concl/total_complete:.1f}%)")
    print(f"  Abstract: {has_abstract}/{total_complete} ({100*has_abstract/total_complete:.1f}%)")
    print(f"  Methodology: {has_method}/{total_complete} ({100*has_method/total_complete:.1f}%)")

conn.close()

# 7. 输出待处理列表
import json

output = {
    'summary': {
        'total': total,
        'complete': len(categories['complete']),
        'in_qdrant_no_chunks': len(categories['in_qdrant_no_chunks']),
        'has_chunks_not_qdrant': len(categories['has_chunks_not_qdrant']),
        'nothing': len(categories['nothing']),
    },
    'priority_1_has_chunks_not_qdrant': [
        {'paper_id': p['paper_id'], 'doi': p['doi'], 'title': p['title'][:80] if p['title'] else None}
        for p in priority_1
    ],
    'priority_2_no_data': [
        {'paper_id': p['paper_id'], 'doi': p['doi'], 'title': p['title'][:80] if p['title'] else None}
        for p in priority_2
    ],
}

with open('data/final_integrity_report.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n📤 已导出详细报告: data/final_integrity_report.json")
