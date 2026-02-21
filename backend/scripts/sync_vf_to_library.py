#!/usr/bin/env python3
"""
Method 2: VF → Library Sync (Abstract Semantic Matching)

Logic:
1. Get Y = VF profiles without item_ID
2. Get X = Library pending filenames
3. For each VF profile in Y:
   - Use Abstract as query
   - Vector search in academic_papers (filtered to X only)
   - If similarity > threshold → match
4. On match:
   - Generate item_ID (ABRxxxxxx)
   - Write item_ID to VF store
   - Write item_ID + full VF metadata to Library (academic_papers)

This is faster than Method 1 (no AI calls) and more robust (semantic matching).
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct, Filter, FieldCondition, MatchValue, MatchAny,
    SearchParams, ScoredPoint
)

# === Configuration ===
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
VF_COLLECTION = "vf_profiles"
LIBRARY_COLLECTION = "academic_papers"

# Matching threshold - Abstract similarity
MATCH_THRESHOLD = 0.85

# Output files
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "library_sync"
PROGRESS_FILE = OUTPUT_DIR / "sync_progress.json"
RESULTS_FILE = OUTPUT_DIR / "sync_results.json"
ID_COUNTER_FILE = OUTPUT_DIR / "id_counter.json"
METHOD2_LOG = OUTPUT_DIR / "method2_results.json"


def get_next_item_id() -> str:
    """Get next item_ID in format ABRxxxxxx."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    if ID_COUNTER_FILE.exists():
        counter = json.loads(ID_COUNTER_FILE.read_text())["counter"]
    else:
        counter = 0
    
    counter += 1
    ID_COUNTER_FILE.write_text(json.dumps({"counter": counter}))
    
    return f"ABR{counter:06d}"


def load_progress() -> dict:
    """Load sync progress from Method 1."""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"processed": [], "matched": [], "pending": [], "exceptions": []}


def save_progress(progress: dict):
    """Save sync progress."""
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2, ensure_ascii=False))


def get_unmatched_vf_profiles(client: QdrantClient) -> list:
    """
    Get Y = VF profiles that don't have item_ID yet.
    Only get meta chunks with in_library=True.
    Abstract is in separate chunk (chunk_id='abstract').
    """
    print("Getting unmatched VF profiles (Y)...")
    
    # Get all meta chunks
    all_meta = []
    offset = None
    while True:
        results, offset = client.scroll(
            VF_COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="chunk_id", match=MatchValue(value="meta"))
            ]),
            limit=500,
            with_payload=True,
            offset=offset
        )
        all_meta.extend(results)
        if offset is None:
            break
    
    # Filter: in_library=True AND no item_id
    unmatched_paper_ids = []
    paper_meta = {}
    for p in all_meta:
        meta = p.payload.get("meta", {})
        paper_id = p.payload.get("paper_id")
        in_library = meta.get("in_library", False)
        item_id = meta.get("item_id")
        
        if in_library and not item_id:
            unmatched_paper_ids.append(paper_id)
            paper_meta[paper_id] = meta
    
    print(f"Found {len(unmatched_paper_ids)} unmatched paper_ids")
    
    # Get abstract chunks for these paper_ids (with vectors)
    unmatched = []
    for paper_id in unmatched_paper_ids:
        results, _ = client.scroll(
            VF_COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="paper_id", match=MatchValue(value=paper_id)),
                FieldCondition(key="chunk_id", match=MatchValue(value="abstract"))
            ]),
            limit=1,
            with_payload=True,
            with_vectors=True
        )
        if results:
            p = results[0]
            unmatched.append({
                "point_id": p.id,
                "paper_id": paper_id,
                "vector": p.vector,
                "meta": paper_meta[paper_id],
                "abstract": p.payload.get("text", "")
            })
    
    print(f"Found {len(unmatched)} with abstract chunks")
    return unmatched


def get_pending_filenames(progress: dict) -> set:
    """Get X = pending filenames from Method 1 progress."""
    return set(progress.get("pending", []))


def find_library_match(
    abstract: str,
    pending_filenames: set,
    client: QdrantClient,
    embedding_vector: list
) -> tuple[str, float] | None:
    """
    Search academic_papers for matching document using abstract vector.
    Only search within pending filenames.
    
    Returns (filename, score) if match found, None otherwise.
    """
    if not pending_filenames:
        return None
    
    # Search using the VF profile's vector (same embedding space)
    results = client.query_points(
        collection_name=LIBRARY_COLLECTION,
        query=embedding_vector,
        query_filter=Filter(must=[
            FieldCondition(
                key="filename",
                match=MatchAny(any=list(pending_filenames))
            )
        ]),
        limit=1,
        with_payload=True,
        score_threshold=MATCH_THRESHOLD
    )
    
    if results.points and results.points[0].score >= MATCH_THRESHOLD:
        filename = results.points[0].payload.get("filename")
        return (filename, results.points[0].score)
    
    return None


def inject_item_id_to_vf(paper_id: str, item_id: str, client: QdrantClient) -> bool:
    """Inject item_ID into VF store meta chunk."""
    try:
        results, _ = client.scroll(
            VF_COLLECTION,
            scroll_filter=Filter(must=[
                FieldCondition(key="paper_id", match=MatchValue(value=paper_id)),
                FieldCondition(key="chunk_id", match=MatchValue(value="meta"))
            ]),
            limit=1,
            with_payload=True,
            with_vectors=True
        )
        
        if not results:
            return False
        
        point = results[0]
        payload = point.payload.copy()
        meta = payload.get("meta", {})
        meta["item_id"] = item_id
        payload["meta"] = meta
        
        client.upsert(
            collection_name=VF_COLLECTION,
            points=[PointStruct(
                id=point.id,
                vector=point.vector,
                payload=payload
            )]
        )
        return True
        
    except Exception as e:
        print(f"    ⚠️ Failed to inject item_ID to VF: {e}")
        return False


def inject_metadata_to_library(
    filename: str,
    item_id: str,
    vf_meta: dict,
    client: QdrantClient
) -> bool:
    """
    Inject item_ID and full VF metadata into Library (academic_papers).
    Updates ALL chunks with this filename.
    """
    try:
        # Find all chunks with this filename
        all_chunks = []
        offset = None
        while True:
            results, offset = client.scroll(
                LIBRARY_COLLECTION,
                scroll_filter=Filter(must=[
                    FieldCondition(key="filename", match=MatchValue(value=filename))
                ]),
                limit=100,
                with_payload=True,
                with_vectors=True,
                offset=offset
            )
            all_chunks.extend(results)
            if offset is None:
                break
        
        if not all_chunks:
            return False
        
        # Update each chunk with item_id and vf_meta
        points_to_upsert = []
        for chunk in all_chunks:
            payload = chunk.payload.copy()
            payload["item_id"] = item_id
            payload["vf_meta"] = vf_meta  # Full VF metadata for future use
            
            points_to_upsert.append(PointStruct(
                id=chunk.id,
                vector=chunk.vector,
                payload=payload
            ))
        
        # Batch upsert
        client.upsert(
            collection_name=LIBRARY_COLLECTION,
            points=points_to_upsert
        )
        
        return True
        
    except Exception as e:
        print(f"    ⚠️ Failed to inject metadata to Library: {e}")
        return False


def run_method2(batch_size: int = None):
    """Run Method 2: VF → Library matching using Abstract."""
    print("=" * 60)
    print("Method 2: VF → Library Sync")
    print("Matching: Abstract Semantic Search")
    print(f"Threshold: {MATCH_THRESHOLD}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Connect to Qdrant
    print("\nConnecting to Qdrant...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Load Method 1 progress to get pending list (X)
    progress = load_progress()
    pending_filenames = get_pending_filenames(progress)
    print(f"Library pending (X): {len(pending_filenames)} files")
    
    if not pending_filenames:
        print("No pending files to match!")
        return
    
    # Get unmatched VF profiles (Y)
    unmatched_vf = get_unmatched_vf_profiles(client)
    
    if not unmatched_vf:
        print("No unmatched VF profiles!")
        return
    
    # Apply batch size if specified
    if batch_size:
        unmatched_vf = unmatched_vf[:batch_size]
        print(f"Processing batch of {len(unmatched_vf)}")
    
    print(f"\nMatching {len(unmatched_vf)} VF profiles against {len(pending_filenames)} pending files...")
    print("-" * 60)
    
    matched_count = 0
    not_matched_count = 0
    start_time = time.time()
    
    for i, vf in enumerate(unmatched_vf, 1):
        paper_id = vf["paper_id"]
        abstract = vf["abstract"]
        meta = vf["meta"]
        vector = vf["vector"]
        
        title = meta.get("title", "")[:50]
        print(f"\n[{i}/{len(unmatched_vf)}] {paper_id}")
        print(f"    Title: {title}...")
        
        # Search using VF's vector
        match = find_library_match(abstract, pending_filenames, client, vector)
        
        if match:
            filename, score = match
            print(f"    ✅ MATCHED! Score: {score:.3f}")
            print(f"    → Library: {filename[:50]}")
            
            # Generate item_ID
            item_id = get_next_item_id()
            print(f"    → Assigned: {item_id}")
            
            # Write to both stores
            inject_item_id_to_vf(paper_id, item_id, client)
            inject_metadata_to_library(filename, item_id, meta, client)
            
            # Update progress - IMMEDIATELY
            if filename in progress["pending"]:
                progress["pending"].remove(filename)
            progress["matched"].append(filename)
            pending_filenames.discard(filename)
            save_progress(progress)  # Write immediately!
            
            # Append result - IMMEDIATELY
            result = {
                "item_id": item_id,
                "vf_paper_id": paper_id,
                "library_filename": filename,
                "score": score,
                "method": "abstract_semantic",
                "timestamp": datetime.now().isoformat()
            }
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            existing_m2 = []
            if METHOD2_LOG.exists():
                existing_m2 = json.loads(METHOD2_LOG.read_text())
            existing_m2.append(result)
            METHOD2_LOG.write_text(json.dumps(existing_m2, indent=2, ensure_ascii=False))
            
            matched_count += 1
        else:
            print(f"    ⏳ No match above threshold")
            not_matched_count += 1
    
    # Summary
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("METHOD 2 COMPLETE")
    print("=" * 60)
    print(f"Processed: {len(unmatched_vf)}")
    print(f"Matched: {matched_count} 🎉")
    print(f"Not matched: {not_matched_count}")
    print(f"Match rate: {100*matched_count/len(unmatched_vf):.1f}%")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(unmatched_vf):.2f}s per item)")
    print(f"\nResults saved to: {METHOD2_LOG}")


if __name__ == "__main__":
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_method2(batch_size)
