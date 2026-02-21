"""
Priority 1 论文导入脚本
将 230 篇有 chunks 文件夹但不在 Qdrant 的论文导入系统

方案 A: 导入 vf_profiles (让 lookup_* 工具工作)
方案 B: 导入 academic_papers (让语义搜索工作)
"""

import json
import sqlite3
import uuid
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件
BACKEND_DIR = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\Agent-B-Research\backend")
load_dotenv(BACKEND_DIR / ".env")

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

# 配置
DATA_DIR = BACKEND_DIR / "data"
SQLITE_PATH = DATA_DIR / "central_index.sqlite"
PLAN_PATH = DATA_DIR / "priority1_fix_plan.json"
CHUNKS_BASE = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks")

# 初始化客户端
qdrant = QdrantClient(host='localhost', port=6333)

# 使用与项目相同的 embedding 模型 (BGE-M3, 1024维)
print("⏳ 加载 BGE-M3 模型...")
model = SentenceTransformer("BAAI/bge-m3")
print("✅ 模型加载完成")

def get_embedding(text: str) -> list[float]:
    """生成文本嵌入向量 (使用 BGE-M3)"""
    return model.encode(text[:8000]).tolist()

def read_section_file(folder_path: Path, section: str) -> Optional[str]:
    """读取章节文件内容"""
    file_path = folder_path / f"{section}.txt"
    if file_path.exists():
        try:
            return file_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"  ⚠️ 读取 {section}.txt 失败: {e}")
    return None

def import_to_vf_profiles(paper: dict, folder_path: Path) -> bool:
    """
    方案 A: 导入到 vf_profiles
    创建一个 meta record，payload 包含论文信息
    """
    paper_id = paper['paper_id']
    clean_id = paper['clean_id']
    
    # 准备 payload
    payload = {
        "paper_id": paper_id,
        "clean_id": clean_id,
        "chunk_id": "meta",
        "chunks_folder": str(folder_path),
        "meta": {
            "title": paper.get('title') or clean_id,
            "year": paper.get('year'),
            "doi": paper.get('doi'),
            "sections": paper.get('txt_files', [])
        }
    }
    
    # 用论文标题或 clean_id 生成 embedding
    text_for_embedding = paper.get('title') or clean_id
    if paper.get('doi'):
        text_for_embedding += f" DOI: {paper['doi']}"
    
    try:
        embedding = get_embedding(text_for_embedding)
        
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload=payload
        )
        
        qdrant.upsert(collection_name="vf_profiles", points=[point])
        return True
    except Exception as e:
        print(f"  ❌ vf_profiles 导入失败: {e}")
        return False

def import_to_academic_papers(paper: dict, folder_path: Path) -> int:
    """
    方案 B: 导入到 academic_papers
    为每个章节创建一个带嵌入的 point
    """
    clean_id = paper['clean_id']
    sections = paper.get('txt_files', [])
    imported = 0
    
    for idx, section in enumerate(sections):
        content = read_section_file(folder_path, section)
        if not content:
            continue
        
        # 截断过长内容
        if len(content) > 8000:
            content = content[:8000]
        
        try:
            embedding = get_embedding(content)
            
            payload = {
                "paper_name": clean_id,
                "filename": f"{clean_id}.md",
                "source": "parsed",
                "section": section,
                "text": content,
                "chunk_index": idx + 1,
                "total_chunks": len(sections),
                "title": paper.get('title'),
                "year": paper.get('year'),
                "doi": paper.get('doi')
            }
            
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload=payload
            )
            
            qdrant.upsert(collection_name="academic_papers", points=[point])
            imported += 1
        except Exception as e:
            print(f"  ❌ academic_papers 导入 {section} 失败: {e}")
    
    return imported

def update_sqlite(paper_id: str, clean_id: str):
    """更新 SQLite 标记"""
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()
    
    # 更新 in_vf_store 和 vf_profile_exists
    cursor.execute("""
        UPDATE papers 
        SET in_vf_store = 1, 
            vf_profile_exists = 1,
            chunks_folder = ?
        WHERE paper_id = ?
    """, (clean_id, paper_id))
    
    conn.commit()
    conn.close()

def main():
    print("=" * 60)
    print("Priority 1 论文导入脚本")
    print("=" * 60)
    
    # 加载计划
    with open(PLAN_PATH, 'r', encoding='utf-8') as f:
        plan = json.load(f)
    
    papers = plan['papers']
    total = len(papers)
    print(f"\n📊 待导入论文数: {total}")
    
    # 统计
    vf_success = 0
    ap_sections = 0
    sqlite_updated = 0
    errors = []
    
    for i, paper in enumerate(papers, 1):
        paper_id = paper['paper_id']
        clean_id = paper['clean_id']
        folder_path = Path(paper['chunks_folder'])
        
        print(f"\n[{i}/{total}] {clean_id[:50]}...")
        
        # 检查文件夹是否存在
        if not folder_path.exists():
            print(f"  ⚠️ 文件夹不存在，跳过")
            errors.append(f"{paper_id}: 文件夹不存在")
            continue
        
        # 方案 A: 导入 vf_profiles
        if import_to_vf_profiles(paper, folder_path):
            vf_success += 1
            print(f"  ✅ vf_profiles 导入成功")
        
        # 方案 B: 导入 academic_papers
        sections_imported = import_to_academic_papers(paper, folder_path)
        ap_sections += sections_imported
        if sections_imported > 0:
            print(f"  ✅ academic_papers 导入 {sections_imported} 个章节")
        
        # 更新 SQLite
        try:
            update_sqlite(paper_id, clean_id)
            sqlite_updated += 1
        except Exception as e:
            print(f"  ❌ SQLite 更新失败: {e}")
    
    # 汇总
    print("\n" + "=" * 60)
    print("📊 导入完成汇总")
    print("=" * 60)
    print(f"✅ vf_profiles 导入: {vf_success}/{total}")
    print(f"✅ academic_papers 章节: {ap_sections}")
    print(f"✅ SQLite 更新: {sqlite_updated}/{total}")
    if errors:
        print(f"❌ 错误数: {len(errors)}")
        for e in errors[:5]:
            print(f"   - {e}")
    
    print("\n🎉 导入完成！")

if __name__ == "__main__":
    main()
