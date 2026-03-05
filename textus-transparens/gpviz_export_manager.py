import os
import json
import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from collections import defaultdict
from models import Code, CodeAssignment, ClusterCode, Cluster

def get_bge_m3_embedding(text, tokenizer, session, max_length=512):
    if not text:
        text = ""
    inputs = tokenizer(text, return_tensors="np", padding=True, truncation=True, max_length=max_length)
    input_ids = inputs["input_ids"].astype(np.int64)
    attention_mask = inputs["attention_mask"].astype(np.int64)
    
    outputs = session.run(None, {"input_ids": input_ids, "attention_mask": attention_mask})
    
    # Extract CLS token embedding
    embeddings = outputs[0][:, 0, :]
    
    # Normalize
    norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / np.maximum(norm, 1e-9)
    return embeddings[0]

def export_gp_viz(project_dir: str):
    db_path = os.path.join(project_dir, "db", "tt.sqlite")
    if not os.path.exists(db_path):
        db_path = os.path.join(project_dir, "db", "project.db")
        
    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)
    db_session = Session()

    # Load ONNX model and tokenizer
    model_path = r"C:\Users\thene\.cache\bge-m3-onnx-npu\bge-m3-int8.onnx"
    tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
    ort_session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])

    # 1. Fetch Codes and Calculate Weights
    codes = db_session.query(Code).filter(Code.status == "active").all()
    code_nodes = []
    code_embeddings = {}
    
    for code in codes:
        # Weight = Assignment count
        weight = db_session.query(CodeAssignment).filter(CodeAssignment.code_id == code.code_id).count()
        
        # Cluster mapping
        cluster_mapping = db_session.query(ClusterCode).filter(ClusterCode.code_id == code.code_id).first()
        cluster_name = None
        if cluster_mapping:
            cluster = db_session.query(Cluster).filter(Cluster.cluster_id == cluster_mapping.cluster_id).first()
            if cluster:
                cluster_name = cluster.name
                
        code_nodes.append({
            "id": str(code.code_id),
            "label": code.name,
            "weight": weight,
            "cluster": cluster_name
        })
        
        # Calculate Embedding (using definition, or fallback to name)
        text_to_embed = code.definition if code.definition else code.name
        code_embeddings[code.code_id] = get_bge_m3_embedding(text_to_embed, tokenizer, ort_session)

    # 2. Calculate Edges
    extract_assignments = db_session.query(CodeAssignment).all()
    extract_to_codes = defaultdict(list)
    for ca in extract_assignments:
        extract_to_codes[ca.extract_id].append(ca.code_id)
        
    co_occurrence = defaultdict(int)
    for c_ids in extract_to_codes.values():
        unique_c_ids = list(set(c_ids))
        for i in range(len(unique_c_ids)):
            for j in range(i + 1, len(unique_c_ids)):
                c1, c2 = sorted([unique_c_ids[i], unique_c_ids[j]])
                co_occurrence[(c1, c2)] += 1
                
    edges = []
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            c1_id = codes[i].code_id
            c2_id = codes[j].code_id
            
            # Semantic Similarity
            sim = float(np.dot(code_embeddings[c1_id], code_embeddings[c2_id]))
            
            # Co-occurrence frequency
            key = tuple(sorted([c1_id, c2_id]))
            co_freq = co_occurrence.get(key, 0)
            
            if sim > 0.4 or co_freq > 0:  # Include edge if there is either some similarity or co-occurrence
                edges.append({
                    "source": str(c1_id),
                    "target": str(c2_id),
                    "co_occurrence": co_freq,
                    "semantic_similarity": sim
                })

    # Prepare final payload
    gp_viz_data = {
        "nodes": code_nodes,
        "edges": edges
    }
    
    export_dir = os.path.join(project_dir, "exports")
    os.makedirs(export_dir, exist_ok=True)
    out_path = os.path.join(export_dir, "semantic_landscape.json")
    
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(gp_viz_data, f, indent=2)
        
    return out_path