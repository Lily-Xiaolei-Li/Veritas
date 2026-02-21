"""Proliferomaxima E2E test — 3 test papers from library.

Picks the same 3 papers used in previous test:
  O'Dwyer et al. 2011, Boiral 2019, Chen 2020

Runs the full pipeline:
  extract refs → AI normalize → dedup → CrossRef resolve → VF generate
"""
import asyncio
import json
import sys
import time
from pathlib import Path

# Ensure backend package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.services.proliferomaxima.batch_engine import ProliferomaximaBatchEngine

TEST_PAPERS = [
    "O'dwyer_2011_seeking_legitimacy_for_new_assura",
    "Boiral_2019_ethical_issues_in_the_assurance_of",
    "Chen_2020_public_family_businesses_and_corpora",
]

PROGRESS_FILE = Path(__file__).parent / "data" / "progress.json"

def write_progress(phase: str, current: int, total: int, status: str = "running", extra: dict = None):
    """Write current progress to progress.json for external monitoring."""
    pct = (current / total * 100) if total > 0 else 0
    data = {
        "phase": phase,
        "current": current,
        "total": total,
        "percent": round(pct, 1),
        "status": status,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    if extra:
        data.update(extra)
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

async def progress(current, total, phase):
    pct = (current / total * 100) if total > 0 else 0
    print(f"  [{current}/{total}] ({pct:.0f}%) — {phase}", flush=True)
    # Also write to progress.json for external monitoring
    write_progress(phase, current, total)

async def main():
    print("=" * 60)
    print("Proliferomaxima E2E Test")
    print("=" * 60)
    start = time.time()

    engine = ProliferomaximaBatchEngine()

    # Check how many .md files we can find
    from app.services.proliferomaxima.paper_selector import find_paper_md_files
    file_map = find_paper_md_files(engine.library_path, TEST_PAPERS)
    print(f"\nPaper files found:")
    for pid in TEST_PAPERS:
        f = file_map.get(pid)
        print(f"  {pid}: {'✅ ' + str(f.name) if f else '❌ not found'}")

    print(f"\nRunning batch engine for {len(TEST_PAPERS)} papers...")
    write_progress("starting", 0, 0, status="running", extra={"papers": len(TEST_PAPERS)})
    result = await engine.run_by_papers(
        paper_ids=TEST_PAPERS,
        require_abstract=True,
        progress_callback=progress,
    )

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"RESULTS (elapsed: {elapsed:.1f}s)")
    print(f"{'=' * 60}")
    print(f"  Total refs extracted: {result['total_refs']}")
    print(f"  Added (new VF profiles): {result['added']}")
    print(f"  Already in VF Store: {result['already_exists']}")
    print(f"  Needs review (no abstract): {result['needs_review']}")
    print(f"  Failed: {result['failed']}")
    print(f"  Cite-how updates: {len(result.get('cite_how_updates', []))}")
    
    if result['needs_review'] > 0:
        print(f"\n  ⚠️  {result['needs_review']} references need manual review.")
        print(f"      Saved to: data/proliferomaxima_needs_review.json")

    # Breakdown of skip reasons
    skip_reasons = {}
    for sr in result.get("skipped_records", []):
        r = sr.get("reason", "unknown")
        skip_reasons[r] = skip_reasons.get(r, 0) + 1
    if skip_reasons:
        print(f"\n  Skip breakdown:")
        for reason, count in sorted(skip_reasons.items(), key=lambda x: -x[1]):
            print(f"    {reason}: {count}")

    # Save full result
    out_path = Path(__file__).parent / "data" / "prolif_e2e_result.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n  Full result saved to: {out_path}")
    
    # Final progress update
    write_progress("complete", result['total_refs'], result['total_refs'], status="completed", extra={
        "added": result['added'],
        "already_exists": result['already_exists'],
        "needs_review": result['needs_review'],
        "failed": result['failed'],
        "elapsed_seconds": round(elapsed, 1),
    })
    print(f"\nDone! 🌸")

if __name__ == "__main__":
    asyncio.run(main())
