#!/usr/bin/env python3
"""
Re-run pending items with new title-first matching logic.
Takes N items from pending list and re-processes them.
"""

import json
import sys
from pathlib import Path

# Import from main sync script
from sync_library_vf import (
    LIBRARY_PATH, OUTPUT_DIR, PROGRESS_FILE, RESULTS_FILE, EXCEPTIONS_FILE,
    extract_metadata_with_ai, load_all_vf_profiles, find_vf_match,
    inject_item_id_to_vf, get_next_item_id, normalize_title, is_book_chapter
)
from qdrant_client import QdrantClient
from datetime import datetime
import time

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333


def rerun_pending(count: int = 50):
    """Re-run pending items with new matching logic."""
    print("=" * 60)
    print("Re-running PENDING items with Title-First Logic")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Count: {count}")
    print("=" * 60)
    
    # Load progress
    if not PROGRESS_FILE.exists():
        print("No progress file found!")
        return
    
    progress = json.loads(PROGRESS_FILE.read_text())
    pending_list = progress.get("pending", [])
    
    # Filter out book chapters
    pending_list = [p for p in pending_list if not is_book_chapter(p)]
    
    print(f"\nTotal pending (excl. book chapters): {len(pending_list)}")
    
    if not pending_list:
        print("No pending items to process!")
        return
    
    # Take first N
    batch = pending_list[:count]
    print(f"Processing: {len(batch)} items")
    print("-" * 60)
    
    # Connect to Qdrant
    print("\nConnecting to Qdrant...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    print("Loading all VF profiles...")
    vf_profiles = load_all_vf_profiles(client)
    print(f"Loaded {len(vf_profiles)} VF profiles")
    
    # Load existing results
    existing_results = []
    if RESULTS_FILE.exists():
        existing_results = json.loads(RESULTS_FILE.read_text())
    
    results = []
    new_matched = []
    still_pending = []
    start_time = time.time()
    
    for i, filename in enumerate(batch, 1):
        print(f"\n[{i}/{len(batch)}] {filename[:55]}...")
        
        md_file = LIBRARY_PATH / filename
        if not md_file.exists():
            print(f"    ⚠️ File not found!")
            still_pending.append(filename)
            continue
        
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            
            print("    → Extracting metadata with AI (incl. title)...")
            extracted = extract_metadata_with_ai(content, filename)
            
            if not extracted:
                print("    ❌ AI extraction failed")
                still_pending.append(filename)
                continue
            
            title = extracted.get("title", "")
            authors = extracted.get("authors", [])
            year = extracted.get("year")
            journal = extracted.get("journal")
            
            title_preview = title[:50] + "..." if len(title) > 50 else title
            print(f"    → Title: {title_preview}")
            print(f"    → {authors[0] if authors else 'N/A'} ({year})")
            
            # Match with new title-first logic
            print("    → Matching (title-first)...")
            vf_match = find_vf_match(title, authors, year, journal, vf_profiles)
            
            if not vf_match:
                print("    ⏳ Still no match")
                still_pending.append(filename)
                results.append({
                    "item_id": "pending",
                    "filename": filename,
                    "extracted": extracted,
                    "reason": "No title match in VF store",
                    "timestamp": datetime.now().isoformat()
                })
                continue
            
            # Success! 
            item_id = get_next_item_id()
            print(f"    ✅ NOW MATCHED! VF: {vf_match['paper_id']}")
            print(f"    → Assigned: {item_id}")
            
            inject_item_id_to_vf(vf_match["paper_id"], item_id, client)
            
            result = {
                "item_id": item_id,
                "filename": filename,
                "vf_paper_id": vf_match["paper_id"],
                "vf_meta": vf_match["meta"],
                "extracted": extracted,
                "timestamp": datetime.now().isoformat()
            }
            results.append(result)
            new_matched.append(filename)
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            still_pending.append(filename)
    
    # Update progress
    # Remove newly matched from pending, add to matched
    progress["pending"] = [p for p in progress["pending"] if p not in new_matched]
    progress["matched"].extend(new_matched)
    
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2, ensure_ascii=False))
    
    # Save results
    existing_results.extend(results)
    RESULTS_FILE.write_text(json.dumps(existing_results, indent=2, ensure_ascii=False))
    
    # Summary
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("RE-RUN COMPLETE")
    print("=" * 60)
    print(f"Processed: {len(batch)}")
    print(f"NEW MATCHES: {len(new_matched)} 🎉")
    print(f"Still pending: {len(still_pending)}")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(batch):.1f}s per paper)")
    
    if new_matched:
        print(f"\nMatch rate improvement: {len(new_matched)}/{len(batch)} = {100*len(new_matched)/len(batch):.1f}%")


if __name__ == "__main__":
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    rerun_pending(count)
