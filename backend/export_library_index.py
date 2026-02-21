# Export Library RAG Index to CSV
import csv
import json
from datetime import datetime
from qdrant_client import QdrantClient

def main():
    print("Connecting to Qdrant...")
    client = QdrantClient(host='localhost', port=6333)
    
    # 获取 collection 信息
    info = client.get_collection('academic_papers')
    print(f"Collection: academic_papers, Points: {info.points_count}")
    
    # 分批提取 unique papers
    unique_papers = {}
    offset = None
    batch = 0
    
    print("Extracting unique papers...")
    while True:
        try:
            points, next_offset = client.scroll(
                'academic_papers', 
                limit=500, 
                offset=offset, 
                with_payload=True, 
                with_vectors=False
            )
        except Exception as e:
            print(f"Error at batch {batch}: {e}")
            break
            
        batch += 1
        
        for p in points:
            fn = p.payload.get('filename', '')
            if fn and fn not in unique_papers:
                unique_papers[fn] = {
                    'item_id': f"LIB_{len(unique_papers)+1:05d}",
                    'filename': fn,
                    'title': p.payload.get('title', ''),
                    'year': p.payload.get('year', ''),
                    'paper_name': p.payload.get('paper_name', ''),
                    'source': p.payload.get('source', ''),
                    'total_chunks': p.payload.get('total_chunks', ''),
                    'section': p.payload.get('section', '')
                }
        
        if batch % 50 == 0:
            print(f"  Batch {batch}: unique papers = {len(unique_papers)}")
        
        if next_offset is None:
            break
        offset = next_offset
    
    print(f"Done! Total unique papers: {len(unique_papers)}")
    
    # 保存到 CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = r"C:\Users\Barry Li (UoN)\OneDrive - The University Of Newcastle\Desktop\AI\Library\RAG index"
    
    # 确保目录存在
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, f"Library_RAG_Index_{timestamp}.csv")
    
    fieldnames = ['item_id', 'filename', 'title', 'year', 'paper_name', 'source', 'total_chunks', 'section']
    
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for paper in unique_papers.values():
            writer.writerow(paper)
    
    print(f"Saved to: {output_path}")
    return output_path

if __name__ == "__main__":
    main()
