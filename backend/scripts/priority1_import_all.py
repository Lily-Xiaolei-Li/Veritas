"""
Priority 1 论文导入脚本 (完整版)
直接从 SQLite 读取所有 CHUNKS_ 开头的论文并导入
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

def get_already_imported() -> set:
    """获取已导入到 vf_profiles 的 paper_id"""
    try:
        # 滚动获取所有已导入的 paper_id
        imported = set()
        offset = None
        while True:
            result = qdrant.scroll(
                collection_name="vf_profiles",
                limit=1000,
                offset=offset,
                with_payload=["paper_id", "clean_id"],
            )
            points, next_offset = result
            if not points:
                break
            for p in points:
                if p.payload:
                    if 'paper_id' in p.payload:
                        imported.add(p.payload['paper_id'])
                    if 'clean_id' in p.payload:
                        imported.add(p.payload['clean_id'])
            if next_offset is None:
                break
            offset = next_offset
        return imported
    except Exception as e:
        print(f"⚠️ 获取已导入列表失败: {e}")
        return set()

def import_to_vf_profiles(paper_id: str, clean_id: str, folder_path: Path, title: str, doi: str, year: int, txt_files: list) -> bool:
    """导入到 vf_profiles"""
    payload = {
        "paper_id": paper_id,
        "clean_id": clean_id,
        "chunk_id": "meta",
        "chunks_folder": str(folder_path),
        "meta": {
            "title": title or clean_id,
            "year": year,
            "doi": doi,
            "sections": txt_files
        }
    }
    
    text_for_embedding = title or clean_id
    if doi:
        text_for_embedding += f" DOI: {doi}"
    
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

def import_to_academic_papers(clean_id: str, folder_path: Path, txt_files: list, title: str, doi: str, year: int) -> int:
    """导入到 academic_papers"""
    imported = 0
    
    for idx, section in enumerate(txt_files):
        content = read_section_file(folder_path, section)
        if not content:
            continue
        
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
                "total_chunks": len(txt_files),
                "title": title,
                "year": year,
                "doi": doi
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
    print("Priority 1 论文导入脚本 (完整版)")
    print("=" * 60)
    
    # 获取已导入的论文
    print("\n⏳ 检查已导入的论文...")
    already_imported = get_already_imported()
    print(f"✅ 已导入 {len(already_imported)} 篇论文")
    
    # 从 SQLite 读取所有 Priority 1 论文
    conn = sqlite3.connect(SQLITE_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT paper_id, chunks_folder, title, doi, year
        FROM papers 
        WHERE paper_id LIKE 'CHUNKS_%'
    """)
    
    papers_to_process = []
    for row in cur.fetchall():
        pid, chunks_folder, title, doi, year = row
        clean_id = pid[7:] if pid.startswith('CHUNKS_') else pid
        
        # 跳过已导入的
        if pid in already_imported or clean_id in already_imported:
            continue
        
        folder_path = CHUNKS_BASE / clean_id
        if folder_path.exists():
            txt_files = [f.stem for f in folder_path.glob('*.txt')]
            papers_to_process.append({
                'paper_id': pid,
                'clean_id': clean_id,
                'folder_path': folder_path,
                'title': title,
                'doi': doi,
                'year': year,
                'txt_files': txt_files
            })
    
    conn.close()
    
    total = len(papers_to_process)
    print(f"\n📊 待导入论文数: {total}")
    
    if total == 0:
        print("✅ 没有需要导入的论文！")
        return
    
    # 统计
    vf_success = 0
    ap_sections = 0
    sqlite_updated = 0
    errors = []
    
    for i, paper in enumerate(papers_to_process, 1):
        paper_id = paper['paper_id']
        clean_id = paper['clean_id']
        folder_path = paper['folder_path']
        
        print(f"\n[{i}/{total}] {clean_id[:50]}...")
        
        # 方案 A: 导入 vf_profiles
        if import_to_vf_profiles(
            paper_id, clean_id, folder_path,
            paper['title'], paper['doi'], paper['year'],
            paper['txt_files']
        ):
            vf_success += 1
            print(f"  ✅ vf_profiles 导入成功")
        
        # 方案 B: 导入 academic_papers
        sections_imported = import_to_academic_papers(
            clean_id, folder_path, paper['txt_files'],
            paper['title'], paper['doi'], paper['year']
        )
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
    
    print("\n🎉 导入完成！")

if __name__ == "__main__":
    main()
