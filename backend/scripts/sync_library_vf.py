#!/usr/bin/env python3
"""
Library ↔ VF Store Sync Script v2
- Primary matching: Title (first 5 words)
- Secondary: Author + Year (±1)
- Assigns item_ID (ABRxxxxxx) to matched papers
"""

import json
import re
import sys
import time
from pathlib import Path
from datetime import datetime

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue

# === Configuration ===
LIBRARY_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")
GATEWAY_URL = "http://localhost:18789"
GATEWAY_TOKEN = "cf8bf99bedae98b1c3feea260670dcb023a0dfb04fddf379"
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
VF_COLLECTION = "vf_profiles"

# Output files
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "library_sync"
PROGRESS_FILE = OUTPUT_DIR / "sync_progress.json"
EXCEPTIONS_FILE = OUTPUT_DIR / "sync_exceptions.json"
RESULTS_FILE = OUTPUT_DIR / "sync_results.json"
ID_COUNTER_FILE = OUTPUT_DIR / "id_counter.json"


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
    """Load sync progress."""
    if PROGRESS_FILE.exists():
        return json.loads(PROGRESS_FILE.read_text())
    return {"processed": [], "matched": [], "pending": [], "exceptions": []}


def save_progress(progress: dict):
    """Save sync progress."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, indent=2, ensure_ascii=False))


def load_exceptions() -> list:
    """Load exceptions list."""
    if EXCEPTIONS_FILE.exists():
        return json.loads(EXCEPTIONS_FILE.read_text())
    return []


def save_exceptions(exceptions: list):
    """Save exceptions list."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    EXCEPTIONS_FILE.write_text(json.dumps(exceptions, indent=2, ensure_ascii=False))


def normalize_title(title: str) -> list:
    """
    Normalize title for matching: lowercase, remove punctuation, get first 5 words.
    Preserves non-English characters (accents, umlauts, etc.)
    """
    if not title:
        return []
    
    # 1. Lowercase (Unicode-aware)
    cleaned = title.lower()
    
    # 2. Remove only specific punctuation, preserve letters from all languages
    # Remove: : ; , . ! ? " ' ( ) [ ] { } / \ | @ # $ % ^ & * + = < > ~ `
    cleaned = re.sub(r'[:;,.!?\"\'\(\)\[\]\{\}/\\|@#$%^&*+=<>~`]+', ' ', cleaned)
    
    # 3. Replace hyphens and underscores with space (so "climate-related" becomes "climate related")
    cleaned = re.sub(r'[-_]+', ' ', cleaned)
    
    # 4. Collapse multiple spaces
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # 5. Split and take first 5 words
    words = cleaned.split()
    return words[:5]


def extract_metadata_with_ai(md_content: str, filename: str) -> dict | None:
    """
    Use Codex 5.3 to extract title, authors, year, journal from MD first page.
    Temperature = 0 for fact matching only.
    """
    first_page = md_content[:1000]
    
    prompt = f"""Extract metadata from this academic paper's first page. Return ONLY valid JSON, no explanation.

First page content:
---
{first_page}
---

Return JSON with these fields (use null if not found):
{{
  "title": "Full paper title",
  "authors": ["First Author", "Second Author"],
  "year": 2024,
  "journal": "Journal Name"
}}

IMPORTANT: 
- title: the full title of the paper (required, this is most important)
- authors: list of author full names
- year: publication year as integer
- journal: publication venue/journal name
- Return ONLY the JSON object, nothing else"""

    headers = {
        "Authorization": f"Bearer {GATEWAY_TOKEN}",
        "Content-Type": "application/json",
        "x-openclaw-agent-id": "coder"
    }
    
    payload = {
        "model": "coder",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 500
    }
    
    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                headers=headers,
                json=payload
            )
            resp.raise_for_status()
            
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            # Parse JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
    except Exception as e:
        print(f"    ⚠️ AI extraction failed: {e}")
        return None


def load_all_vf_profiles(client: QdrantClient) -> list:
    """Load all VF profile meta chunks into memory."""
    all_profiles = []
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
        all_profiles.extend(results)
        if offset is None:
            break
    return all_profiles


def find_vf_match(title: str, authors: list, year: int, journal: str, vf_profiles: list) -> dict | None:
    """
    Find matching VF profile.
    
    MATCHING LOGIC (priority order):
    1. PRIMARY: Title first 5 words must match exactly
    2. SECONDARY: If title matches, verify with author OR year (±1)
    
    Title is the strongest signal - if first 5 words match, 
    it's almost certainly the same paper.
    """
    if not title:
        return None
    
    # Normalize extracted title
    extracted_title_words = normalize_title(title)
    if len(extracted_title_words) < 3:
        # Title too short, unreliable
        return None
    
    # Get first author last name for secondary check
    first_author_last = ""
    if authors and authors[0]:
        first_author_last = authors[0].split()[-1].lower()
    
    matches = []
    
    for point in vf_profiles:
        meta = point.payload.get("meta", {})
        vf_title = meta.get("title", "")
        vf_year = meta.get("year")
        vf_authors = meta.get("authors", [])
        
        # PRIMARY CHECK: Title first 5 words
        vf_title_words = normalize_title(vf_title)
        if not vf_title_words:
            continue
        
        # Compare title words (must match exactly)
        if extracted_title_words != vf_title_words:
            continue
        
        # Title matches! Now do secondary verification
        score = 0
        
        # Check author
        if vf_authors and first_author_last:
            vf_first_author_last = vf_authors[0].split()[-1].lower() if vf_authors[0] else ""
            if first_author_last == vf_first_author_last:
                score += 2
        
        # Check year (±1 tolerance)
        if year and vf_year:
            if year == vf_year:
                score += 2
            elif abs(year - vf_year) == 1:
                score += 1
        
        matches.append({
            "point_id": point.id,
            "paper_id": point.payload.get("paper_id"),
            "meta": meta,
            "score": score,
            "vf_title": vf_title
        })
    
    if not matches:
        return None
    
    # If only one title match, return it (title is strong enough)
    if len(matches) == 1:
        return matches[0]
    
    # Multiple title matches (rare) - pick highest score
    matches.sort(key=lambda x: x["score"], reverse=True)
    if matches[0]["score"] > matches[1]["score"]:
        return matches[0]
    
    # Ambiguous - return None
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


def is_book_chapter(filename: str) -> bool:
    """Check if file is a book chapter (Springer format)."""
    # Springer book chapters: 10.1007_978-3-...
    return "978-3-" in filename


def process_batch(batch_size: int = 5):
    """Process a batch of library papers."""
    print("=" * 60)
    print("Library ↔ VF Store Sync v2")
    print("Matching: Title (first 5 words) + Author/Year verification")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Batch size: {batch_size}")
    print("=" * 60)
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    progress = load_progress()
    exceptions = load_exceptions()
    
    print("\nConnecting to Qdrant...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    print("Loading all VF profiles...")
    vf_profiles = load_all_vf_profiles(client)
    print(f"Loaded {len(vf_profiles)} VF profiles")
    
    # Get all MD files, excluding book chapters
    all_files = sorted(LIBRARY_PATH.glob("*.md"))
    all_files = [f for f in all_files if not is_book_chapter(f.name)]
    print(f"Total library files (excl. book chapters): {len(all_files)}")
    
    # Filter out already processed
    processed_set = set(progress.get("processed", []))
    pending = [f for f in all_files if f.name not in processed_set]
    print(f"Already processed: {len(processed_set)}")
    print(f"Pending: {len(pending)}")
    
    batch = pending[:batch_size]
    print(f"\nProcessing batch of {len(batch)} files...")
    print("-" * 60)
    
    results = []
    start_time = time.time()
    
    for i, md_file in enumerate(batch, 1):
        print(f"\n[{i}/{len(batch)}] {md_file.name[:55]}...")
        
        try:
            content = md_file.read_text(encoding="utf-8", errors="ignore")
            
            print("    → Extracting metadata with AI...")
            extracted = extract_metadata_with_ai(content, md_file.name)
            
            if not extracted:
                print("    ❌ AI extraction failed")
                exceptions.append({
                    "filename": md_file.name,
                    "reason": "AI extraction failed",
                    "timestamp": datetime.now().isoformat()
                })
                progress["processed"].append(md_file.name)
                progress["exceptions"].append(md_file.name)
                continue
            
            title = extracted.get("title", "")
            authors = extracted.get("authors", [])
            year = extracted.get("year")
            journal = extracted.get("journal")
            
            title_preview = title[:50] + "..." if len(title) > 50 else title
            print(f"    → Title: {title_preview}")
            print(f"    → {authors[0] if authors else 'N/A'} ({year}) - {journal or 'N/A'}")
            
            # Find VF match using title-first logic
            print("    → Matching in VF store (title-first)...")
            vf_match = find_vf_match(title, authors, year, journal, vf_profiles)
            
            if not vf_match:
                print("    ⏳ No VF match - marking as PENDING")
                pending_result = {
                    "item_id": "pending",
                    "filename": md_file.name,
                    "extracted": extracted,
                    "reason": "No title match in VF store",
                    "timestamp": datetime.now().isoformat()
                }
                results.append(pending_result)
                progress["processed"].append(md_file.name)
                progress["pending"].append(md_file.name)
                continue
            
            # Success!
            item_id = get_next_item_id()
            print(f"    ✅ Matched! VF: {vf_match['paper_id']}")
            print(f"    → Assigned: {item_id}")
            
            inject_item_id_to_vf(vf_match["paper_id"], item_id, client)
            
            result = {
                "item_id": item_id,
                "filename": md_file.name,
                "vf_paper_id": vf_match["paper_id"],
                "vf_meta": vf_match["meta"],
                "extracted": extracted,
                "timestamp": datetime.now().isoformat()
            }
            results.append(result)
            
            progress["processed"].append(md_file.name)
            progress["matched"].append(md_file.name)
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            exceptions.append({
                "filename": md_file.name,
                "reason": str(e),
                "timestamp": datetime.now().isoformat()
            })
            progress["processed"].append(md_file.name)
            progress["exceptions"].append(md_file.name)
    
    save_progress(progress)
    save_exceptions(exceptions)
    
    if results:
        existing_results = []
        if RESULTS_FILE.exists():
            existing_results = json.loads(RESULTS_FILE.read_text())
        existing_results.extend(results)
        RESULTS_FILE.write_text(json.dumps(existing_results, indent=2, ensure_ascii=False))
    
    # Summary
    elapsed = time.time() - start_time
    matched_count = len([r for r in results if r.get("item_id", "").startswith("ABR")])
    pending_count = len([r for r in results if r.get("item_id") == "pending"])
    exception_count = len(batch) - len(results)
    
    print("\n" + "=" * 60)
    print("BATCH COMPLETE")
    print("=" * 60)
    print(f"Processed: {len(batch)}")
    print(f"Matched (ABR): {matched_count}")
    print(f"Pending (not in VF): {pending_count}")
    print(f"Exceptions: {exception_count}")
    print(f"Time: {elapsed:.1f}s ({elapsed/len(batch):.1f}s per paper)")
    
    if len(pending) > batch_size:
        remaining = len(pending) - batch_size
        print(f"\nRemaining: {remaining} papers")
        est_time = remaining * (elapsed / len(batch))
        print(f"Estimated time for rest: {est_time/60:.1f} minutes")


if __name__ == "__main__":
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    process_batch(batch_size)
