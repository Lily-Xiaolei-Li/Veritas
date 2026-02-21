"""
Library CLI Handlers

Commands for managing and diagnosing the research library.
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from .contract import CLIBusinessError, success_envelope

# Configuration
QDRANT_URL = "http://localhost:6333"
CENTRAL_DB = Path(__file__).parent.parent / "data" / "central_index.sqlite"
CHUNKS_DIR = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\chunks")


def _get_db_connection() -> sqlite3.Connection:
    """Get SQLite connection with error handling."""
    if not CENTRAL_DB.exists():
        raise CLIBusinessError(
            code="LIBRARY_DB_NOT_FOUND",
            message=f"Central index database not found: {CENTRAL_DB}",
        )
    return sqlite3.connect(str(CENTRAL_DB))


def _get_qdrant_paper_ids() -> set[str]:
    """Get all paper_ids from Qdrant vf_profiles collection."""
    try:
        response = requests.post(
            f"{QDRANT_URL}/collections/vf_profiles/points/scroll",
            json={"limit": 10000, "with_payload": ["paper_id"], "with_vector": False},
            timeout=30,
        )
        if response.status_code != 200:
            return set()
        
        paper_ids = set()
        for p in response.json().get("result", {}).get("points", []):
            pid = p.get("payload", {}).get("paper_id")
            if pid:
                paper_ids.add(pid)
        return paper_ids
    except requests.RequestException:
        return set()


def _get_qdrant_paper_chunks() -> dict[str, set[str]]:
    """Get paper_id -> chunk_ids mapping from Qdrant."""
    try:
        response = requests.post(
            f"{QDRANT_URL}/collections/vf_profiles/points/scroll",
            json={"limit": 10000, "with_payload": ["paper_id", "chunk_id"], "with_vector": False},
            timeout=30,
        )
        if response.status_code != 200:
            return {}
        
        paper_chunks: dict[str, set[str]] = {}
        for pt in response.json().get("result", {}).get("points", []):
            pid = pt.get("payload", {}).get("paper_id")
            cid = pt.get("payload", {}).get("chunk_id")
            if pid:
                if pid not in paper_chunks:
                    paper_chunks[pid] = set()
                if cid:
                    paper_chunks[pid].add(cid)
        return paper_chunks
    except requests.RequestException:
        return {}


def library_status(args) -> dict[str, Any]:
    """
    Library status overview.
    
    Returns basic statistics about the library.
    """
    conn = _get_db_connection()
    cur = conn.cursor()
    
    try:
        # Basic counts
        cur.execute("SELECT COUNT(*) FROM papers")
        total = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM papers WHERE in_vf_store = 1")
        in_vf = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM papers WHERE has_chunks_folder = 1")
        has_chunks = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM papers WHERE in_excel_index = 1")
        in_excel = cur.fetchone()[0]
        
        # Section coverage
        sections = {}
        for sec in ['abstract', 'introduction', 'methodology', 'conclusion']:
            cur.execute(f"SELECT COUNT(*) FROM papers WHERE has_{sec} = 1")
            sections[sec] = cur.fetchone()[0]
        
        # Canonical ID coverage
        cur.execute("SELECT COUNT(*) FROM papers WHERE canonical_id IS NOT NULL AND canonical_id != ''")
        has_canonical = cur.fetchone()[0]
        
        # Check for duplicates
        cur.execute("SELECT COUNT(*) FROM (SELECT paper_id FROM papers GROUP BY paper_id HAVING COUNT(*) > 1)")
        duplicate_count = cur.fetchone()[0]
        
        # Chunk statistics
        cur.execute("""
            SELECT MIN(lib_chunk_count), MAX(lib_chunk_count), AVG(lib_chunk_count) 
            FROM papers WHERE lib_chunk_count > 0
        """)
        chunk_stats = cur.fetchone()
        
        conn.close()
        
        return success_envelope(
            result="ok",
            data={
                "total_papers": total,
                "in_vf_store": in_vf,
                "has_chunks_folder": has_chunks,
                "in_excel_index": in_excel,
                "has_canonical_id": has_canonical,
                "duplicate_paper_ids": duplicate_count,
                "section_coverage": sections,
                "chunk_stats": {
                    "min": chunk_stats[0],
                    "max": chunk_stats[1],
                    "avg": round(chunk_stats[2], 1) if chunk_stats[2] else None,
                },
                "completeness_pct": round(100 * has_chunks / total, 1) if total > 0 else 0,
            },
        )
    except Exception as e:
        conn.close()
        raise CLIBusinessError(
            code="LIBRARY_STATUS_ERROR",
            message="Failed to get library status",
            details=str(e),
        )


def library_check(args) -> dict[str, Any]:
    """
    Full integrity check.
    
    Cross-checks SQLite with Qdrant and chunks folders.
    """
    conn = _get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get Qdrant data
        qdrant_ids = _get_qdrant_paper_ids()
        qdrant_available = len(qdrant_ids) > 0
        
        # Get all papers from SQLite
        cur.execute("""
            SELECT paper_id, title, doi, in_vf_store, has_chunks_folder,
                   has_abstract, has_introduction, has_methodology, has_conclusion
            FROM papers
        """)
        
        categories = {
            "complete": [],
            "in_qdrant_no_chunks": [],
            "has_chunks_not_qdrant": [],
            "nothing": [],
        }
        
        for row in cur.fetchall():
            pid, title, doi, in_vf_db, has_chunks, has_abs, has_intro, has_meth, has_conc = row
            
            in_qdrant = pid in qdrant_ids if qdrant_available else bool(in_vf_db)
            
            paper_info = {
                "paper_id": pid,
                "title": title[:80] + "..." if title and len(title) > 80 else title,
                "doi": doi,
                "has_intro": bool(has_intro),
                "has_conclusion": bool(has_conc),
            }
            
            if in_qdrant and has_chunks:
                categories["complete"].append(paper_info)
            elif in_qdrant and not has_chunks:
                categories["in_qdrant_no_chunks"].append(paper_info)
            elif not in_qdrant and has_chunks:
                categories["has_chunks_not_qdrant"].append(paper_info)
            else:
                categories["nothing"].append(paper_info)
        
        conn.close()
        
        # Priority lists (only papers with title or DOI)
        priority_1 = [p for p in categories["has_chunks_not_qdrant"] if p["title"] or p["doi"]]
        priority_2 = [p for p in categories["nothing"] if p["title"] or p["doi"]]
        priority_3 = [p for p in categories["in_qdrant_no_chunks"] if p["title"] or p["doi"]]
        
        return success_envelope(
            result="ok",
            data={
                "qdrant_available": qdrant_available,
                "summary": {
                    "complete": len(categories["complete"]),
                    "in_qdrant_no_chunks": len(categories["in_qdrant_no_chunks"]),
                    "has_chunks_not_qdrant": len(categories["has_chunks_not_qdrant"]),
                    "nothing": len(categories["nothing"]),
                },
                "priorities": {
                    "p1_has_chunks_not_qdrant": len(priority_1),
                    "p2_no_data": len(priority_2),
                    "p3_qdrant_no_chunks": len(priority_3),
                },
                "priority_1_sample": priority_1[:10],
                "priority_2_sample": priority_2[:10],
            },
        )
    except Exception as e:
        conn.close()
        raise CLIBusinessError(
            code="LIBRARY_CHECK_ERROR",
            message="Integrity check failed",
            details=str(e),
        )


def library_gaps(args) -> dict[str, Any]:
    """
    Data gap analysis.
    
    Find papers missing sections, cross-reference issues, etc.
    """
    priority_filter = getattr(args, "priority", None)
    
    conn = _get_db_connection()
    cur = conn.cursor()
    
    try:
        # Cross-checks
        cur.execute("""SELECT COUNT(*) FROM papers 
            WHERE in_excel_index = 1 AND (in_vf_store = 0 OR in_vf_store IS NULL)""")
        excel_not_vf = cur.fetchone()[0]
        
        cur.execute("""SELECT COUNT(*) FROM papers 
            WHERE in_vf_store = 1 AND (in_excel_index = 0 OR in_excel_index IS NULL)""")
        vf_not_excel = cur.fetchone()[0]
        
        cur.execute("""SELECT COUNT(*) FROM papers 
            WHERE has_chunks_folder = 1 AND (in_vf_store = 0 OR in_vf_store IS NULL)""")
        chunks_not_vf = cur.fetchone()[0]
        
        cur.execute("""SELECT COUNT(*) FROM papers 
            WHERE in_vf_store = 1 AND (has_chunks_folder = 0 OR has_chunks_folder IS NULL)""")
        vf_no_chunks = cur.fetchone()[0]
        
        # Section completeness
        cur.execute("""SELECT COUNT(*) FROM papers 
            WHERE has_abstract = 1 AND has_introduction = 1 
            AND has_methodology = 1 AND has_conclusion = 1""")
        all_sections = cur.fetchone()[0]
        
        cur.execute("""SELECT COUNT(*) FROM papers 
            WHERE (has_abstract = 0 OR has_abstract IS NULL)
            AND (has_introduction = 0 OR has_introduction IS NULL)
            AND (has_methodology = 0 OR has_methodology IS NULL)
            AND (has_conclusion = 0 OR has_conclusion IS NULL)""")
        no_sections = cur.fetchone()[0]
        
        # Papers with few chunks
        cur.execute("""SELECT paper_id, lib_chunk_count FROM papers 
            WHERE lib_chunk_count > 0 AND lib_chunk_count < 5""")
        few_chunks = [{"paper_id": r[0], "chunk_count": r[1]} for r in cur.fetchall()]
        
        # Year distribution (top 10)
        cur.execute("""SELECT year, COUNT(*) FROM papers 
            WHERE year IS NOT NULL 
            GROUP BY year ORDER BY year DESC LIMIT 10""")
        year_dist = {str(r[0]): r[1] for r in cur.fetchall()}
        
        cur.execute("SELECT COUNT(*) FROM papers WHERE year IS NULL")
        no_year = cur.fetchone()[0]
        
        # Gap details by priority
        gap_details = {}
        
        if priority_filter is None or priority_filter == 1:
            # Priority 1: has chunks but not in VF Store
            cur.execute("""
                SELECT paper_id, title, doi FROM papers 
                WHERE has_chunks_folder = 1 AND (in_vf_store = 0 OR in_vf_store IS NULL)
                AND (title IS NOT NULL OR doi IS NOT NULL)
            """)
            gap_details["priority_1"] = [
                {"paper_id": r[0], "title": r[1][:60] + "..." if r[1] and len(r[1]) > 60 else r[1], "doi": r[2]}
                for r in cur.fetchall()
            ]
        
        if priority_filter is None or priority_filter == 2:
            # Priority 2: neither chunks nor VF Store
            cur.execute("""
                SELECT paper_id, title, doi FROM papers 
                WHERE (has_chunks_folder = 0 OR has_chunks_folder IS NULL)
                AND (in_vf_store = 0 OR in_vf_store IS NULL)
                AND (title IS NOT NULL OR doi IS NOT NULL)
            """)
            gap_details["priority_2"] = [
                {"paper_id": r[0], "title": r[1][:60] + "..." if r[1] and len(r[1]) > 60 else r[1], "doi": r[2]}
                for r in cur.fetchall()
            ]
        
        if priority_filter is None or priority_filter == 3:
            # Priority 3: in VF Store but no chunks
            cur.execute("""
                SELECT paper_id, title, doi FROM papers 
                WHERE in_vf_store = 1 AND (has_chunks_folder = 0 OR has_chunks_folder IS NULL)
                AND (title IS NOT NULL OR doi IS NOT NULL)
            """)
            gap_details["priority_3"] = [
                {"paper_id": r[0], "title": r[1][:60] + "..." if r[1] and len(r[1]) > 60 else r[1], "doi": r[2]}
                for r in cur.fetchall()
            ]
        
        conn.close()
        
        return success_envelope(
            result="ok",
            data={
                "cross_reference": {
                    "excel_not_vf": excel_not_vf,
                    "vf_not_excel": vf_not_excel,
                    "chunks_not_vf": chunks_not_vf,
                    "vf_no_chunks": vf_no_chunks,
                },
                "section_coverage": {
                    "all_four_sections": all_sections,
                    "no_sections": no_sections,
                },
                "few_chunks_papers": few_chunks[:20],
                "year_distribution": year_dist,
                "no_year_count": no_year,
                "gap_details": gap_details,
            },
        )
    except Exception as e:
        conn.close()
        raise CLIBusinessError(
            code="LIBRARY_GAPS_ERROR",
            message="Gap analysis failed",
            details=str(e),
        )


def library_match(args) -> dict[str, Any]:
    """
    Paper matching check.
    
    Check how a paper_id matches with chunks folder and Qdrant.
    """
    paper_id = getattr(args, "paper_id", None)
    if not paper_id:
        raise CLIBusinessError(
            code="LIBRARY_MATCH_MISSING_PAPER_ID",
            message="--paper-id is required",
        )
    
    conn = _get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get paper from SQLite
        cur.execute("""
            SELECT paper_id, title, doi, year, chunks_folder,
                   in_vf_store, has_chunks_folder,
                   has_abstract, has_introduction, has_methodology, has_conclusion,
                   canonical_id, lib_chunk_count
            FROM papers WHERE paper_id = ?
        """, (paper_id,))
        row = cur.fetchone()
        
        if not row:
            conn.close()
            raise CLIBusinessError(
                code="LIBRARY_PAPER_NOT_FOUND",
                message=f"Paper not found: {paper_id}",
            )
        
        (pid, title, doi, year, chunks_folder, in_vf, has_chunks,
         has_abs, has_intro, has_meth, has_conc, canonical_id, chunk_count) = row
        
        conn.close()
        
        # Check chunks folder
        chunks_match = None
        chunks_files = []
        if chunks_folder:
            folder_path = Path(chunks_folder)
            if folder_path.exists():
                chunks_match = "exact"
                chunks_files = [f.name for f in folder_path.iterdir() if f.is_file()][:20]
            else:
                # Try to find in CHUNKS_DIR
                clean_name = pid[7:] if pid.startswith("CHUNKS_") else pid
                alt_path = CHUNKS_DIR / clean_name
                if alt_path.exists():
                    chunks_match = "by_name"
                    chunks_files = [f.name for f in alt_path.iterdir() if f.is_file()][:20]
                else:
                    chunks_match = "not_found"
        else:
            # Try to infer chunks folder
            clean_name = pid[7:] if pid.startswith("CHUNKS_") else pid
            possible_path = CHUNKS_DIR / clean_name
            if possible_path.exists():
                chunks_match = "inferred"
                chunks_files = [f.name for f in possible_path.iterdir() if f.is_file()][:20]
            else:
                chunks_match = "none"
        
        # Check Qdrant
        qdrant_status = {"found": False, "pieces": 0, "chunk_ids": []}
        try:
            response = requests.post(
                f"{QDRANT_URL}/collections/vf_profiles/points/scroll",
                json={
                    "filter": {"must": [{"key": "paper_id", "match": {"value": paper_id}}]},
                    "limit": 20,
                    "with_payload": ["chunk_id"],
                    "with_vector": False,
                },
                timeout=10,
            )
            if response.status_code == 200:
                points = response.json().get("result", {}).get("points", [])
                if points:
                    qdrant_status["found"] = True
                    qdrant_status["pieces"] = len(points)
                    qdrant_status["chunk_ids"] = [
                        p.get("payload", {}).get("chunk_id") for p in points
                    ]
        except requests.RequestException:
            qdrant_status["error"] = "Connection failed"
        
        return success_envelope(
            result="ok",
            data={
                "paper": {
                    "paper_id": pid,
                    "title": title,
                    "doi": doi,
                    "year": year,
                    "canonical_id": canonical_id,
                },
                "sqlite_status": {
                    "in_vf_store": bool(in_vf),
                    "has_chunks_folder": bool(has_chunks),
                    "chunk_count": chunk_count,
                    "sections": {
                        "abstract": bool(has_abs),
                        "introduction": bool(has_intro),
                        "methodology": bool(has_meth),
                        "conclusion": bool(has_conc),
                    },
                },
                "chunks_folder": {
                    "match_type": chunks_match,
                    "path": chunks_folder,
                    "files_sample": chunks_files,
                },
                "qdrant_status": qdrant_status,
            },
        )
    except CLIBusinessError:
        raise
    except Exception as e:
        raise CLIBusinessError(
            code="LIBRARY_MATCH_ERROR",
            message=f"Match check failed for {paper_id}",
            details=str(e),
        )


def library_vf_status(args) -> dict[str, Any]:
    """
    VF Store status check.
    
    Analyze the 8-piece vector structure in Qdrant.
    """
    try:
        # Check collection exists
        response = requests.get(f"{QDRANT_URL}/collections/vf_profiles", timeout=10)
        if response.status_code != 200:
            return success_envelope(
                result="ok",
                data={
                    "available": False,
                    "error": "Collection vf_profiles not found",
                },
            )
        
        collection_info = response.json().get("result", {})
        
        # Get all papers and their chunks
        paper_chunks = _get_qdrant_paper_chunks()
        
        if not paper_chunks:
            return success_envelope(
                result="ok",
                data={
                    "available": True,
                    "total_papers": 0,
                    "points_count": collection_info.get("points_count", 0),
                },
            )
        
        # Analyze piece distribution
        piece_distribution: dict[int, int] = {}
        for chunks in paper_chunks.values():
            count = len(chunks)
            piece_distribution[count] = piece_distribution.get(count, 0) + 1
        
        # Find papers with complete 8 pieces
        complete_8 = [pid for pid, chunks in paper_chunks.items() if len(chunks) == 8]
        
        # Get sample of 8-piece structure
        piece_structure_sample = None
        if complete_8:
            sample_pid = complete_8[0]
            piece_structure_sample = {
                "paper_id": sample_pid,
                "pieces": sorted(list(paper_chunks[sample_pid])),
            }
        
        return success_envelope(
            result="ok",
            data={
                "available": True,
                "collection": {
                    "points_count": collection_info.get("points_count", 0),
                    "vectors_count": collection_info.get("vectors_count", 0),
                },
                "total_papers": len(paper_chunks),
                "complete_8_pieces": len(complete_8),
                "piece_distribution": {str(k): v for k, v in sorted(piece_distribution.items())},
                "structure_sample": piece_structure_sample,
            },
        )
    except requests.RequestException as e:
        return success_envelope(
            result="ok",
            data={
                "available": False,
                "error": f"Connection failed: {e}",
            },
        )


def library_fix(args) -> dict[str, Any]:
    """
    Generate fix plan for library issues.
    
    Analyzes what needs to be fixed and generates a plan.
    """
    priority = getattr(args, "priority", None)
    dry_run = getattr(args, "dry_run", True)
    
    if priority not in [1, 2, 3]:
        raise CLIBusinessError(
            code="LIBRARY_FIX_INVALID_PRIORITY",
            message="--priority must be 1, 2, or 3",
        )
    
    conn = _get_db_connection()
    cur = conn.cursor()
    
    try:
        fix_plan = {
            "priority": priority,
            "dry_run": dry_run,
            "actions": [],
            "stats": {},
        }
        
        if priority == 1:
            # Priority 1: Papers with chunks but not in Qdrant
            cur.execute("""
                SELECT paper_id, chunks_folder, title, doi, year, authors_json
                FROM papers 
                WHERE paper_id LIKE 'CHUNKS_%'
            """)
            
            papers_to_fix = []
            for row in cur.fetchall():
                pid, chunks_folder, title, doi, year, authors_json = row
                
                # Get clean folder name
                folder_name = pid[7:] if pid.startswith("CHUNKS_") else pid
                folder_path = CHUNKS_DIR / folder_name
                
                if folder_path.exists():
                    txt_files = [f.stem for f in folder_path.glob("*.txt")]
                    json_files = [f.name for f in folder_path.glob("*.json")]
                    
                    papers_to_fix.append({
                        "paper_id": pid,
                        "clean_id": folder_name,
                        "chunks_folder": str(folder_path),
                        "title": title[:60] + "..." if title and len(title) > 60 else title,
                        "doi": doi,
                        "year": year,
                        "txt_files": txt_files[:10],
                        "json_files": json_files[:5],
                        "has_meta_json": any("meta" in f.lower() for f in json_files),
                    })
            
            # Stats
            has_title = sum(1 for p in papers_to_fix if p["title"])
            has_doi = sum(1 for p in papers_to_fix if p["doi"])
            has_year = sum(1 for p in papers_to_fix if p["year"])
            has_meta = sum(1 for p in papers_to_fix if p["has_meta_json"])
            
            fix_plan["stats"] = {
                "total_papers": len(papers_to_fix),
                "with_title": has_title,
                "with_doi": has_doi,
                "with_year": has_year,
                "with_meta_json": has_meta,
            }
            
            fix_plan["actions"] = [
                {
                    "action": "create_vf_meta_records",
                    "description": "Create vf_profiles meta record for each paper",
                    "count": len(papers_to_fix),
                },
                {
                    "action": "update_sqlite_chunks_folder",
                    "description": "Update papers.chunks_folder to correct path",
                    "count": len(papers_to_fix),
                },
            ]
            
            fix_plan["papers_sample"] = papers_to_fix[:20]
            fix_plan["recommendation"] = (
                "Run 'vf sync' or create a batch import script to add these papers to vf_profiles."
            )
            
        elif priority == 2:
            # Priority 2: No chunks, no VF Store
            cur.execute("""
                SELECT paper_id, title, doi FROM papers 
                WHERE (has_chunks_folder = 0 OR has_chunks_folder IS NULL)
                AND (in_vf_store = 0 OR in_vf_store IS NULL)
                AND (title IS NOT NULL OR doi IS NOT NULL)
            """)
            papers = [{"paper_id": r[0], "title": r[1], "doi": r[2]} for r in cur.fetchall()]
            
            with_doi = sum(1 for p in papers if p["doi"])
            
            fix_plan["stats"] = {
                "total_papers": len(papers),
                "with_doi": with_doi,
            }
            
            fix_plan["actions"] = [
                {
                    "action": "download_pdfs",
                    "description": "Download PDFs for papers with DOI",
                    "count": with_doi,
                },
                {
                    "action": "generate_chunks",
                    "description": "Parse PDFs and generate chunks",
                    "count": with_doi,
                },
                {
                    "action": "import_to_vf",
                    "description": "Generate VF profiles and import to Qdrant",
                    "count": with_doi,
                },
            ]
            
            fix_plan["papers_sample"] = papers[:20]
            fix_plan["recommendation"] = (
                "Use 'source proxy-download' to queue DOIs for download, then process with library pipeline."
            )
            
        elif priority == 3:
            # Priority 3: In VF Store but no chunks
            cur.execute("""
                SELECT paper_id, title, doi FROM papers 
                WHERE in_vf_store = 1 
                AND (has_chunks_folder = 0 OR has_chunks_folder IS NULL)
                AND (title IS NOT NULL OR doi IS NOT NULL)
            """)
            papers = [{"paper_id": r[0], "title": r[1], "doi": r[2]} for r in cur.fetchall()]
            
            fix_plan["stats"] = {"total_papers": len(papers)}
            
            fix_plan["actions"] = [
                {
                    "action": "identify_source",
                    "description": "Identify original PDF or source for these papers",
                    "count": len(papers),
                },
                {
                    "action": "generate_chunks",
                    "description": "Generate chunks from source",
                    "count": len(papers),
                },
            ]
            
            fix_plan["papers_sample"] = papers[:20]
            fix_plan["recommendation"] = (
                "These papers were likely imported directly to VF Store. "
                "Find original PDFs to generate chunks for section_lookup."
            )
        
        conn.close()
        
        if not dry_run:
            fix_plan["executed"] = False
            fix_plan["note"] = "Actual execution not yet implemented. Use dry-run to see plan."
        
        return success_envelope(result="ok", data=fix_plan)
        
    except Exception as e:
        conn.close()
        raise CLIBusinessError(
            code="LIBRARY_FIX_ERROR",
            message=f"Fix plan generation failed for priority {priority}",
            details=str(e),
        )


def library_export(args) -> dict[str, Any]:
    """
    Export library database to CSV or JSON.
    
    Exports all papers with comprehensive metadata for analysis in Excel or other tools.
    """
    # Get output path
    output = getattr(args, "output", None)
    output_format = getattr(args, "format", "csv")
    include_paths = getattr(args, "include_paths", False)
    
    # Generate default filename with timestamp if not provided
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = "json" if output_format == "json" else "csv"
        output = f"library_export_{timestamp}.{ext}"
    
    conn = _get_db_connection()
    cur = conn.cursor()
    
    try:
        # Query all data with proper column aliasing
        cur.execute("""
            SELECT 
                paper_id,
                canonical_id,
                doi,
                title,
                authors_json,
                year,
                journal,
                paper_type,
                primary_method,
                keywords_json,
                in_vf_store,
                in_excel_index,
                has_chunks_folder,
                lib_chunk_count,
                has_abstract,
                has_introduction,
                has_methodology,
                has_conclusion,
                vf_profile_exists,
                vf_chunks_generated,
                pdf_filename,
                chunks_folder,
                created_at,
                updated_at
            FROM papers
            ORDER BY paper_id
        """)
        
        rows = cur.fetchall()
        conn.close()
        
        # Define output columns
        columns = [
            "item_id",
            "canonical_id",
            "doi",
            "title",
            "authors",
            "year",
            "journal",
            "paper_type",
            "primary_method",
            "keywords",
            "in_vf_store",
            "in_excel_index",
            "has_chunks",
            "chunk_count",
            "has_abstract",
            "has_introduction",
            "has_methodology",
            "has_conclusion",
            "vf_profile_exists",
            "vf_chunks_count",
            "pdf_filename",
            "chunks_folder",
            "created_at",
            "updated_at",
        ]
        
        # include_paths flag is reserved for future use (e.g., absolute vs relative paths)
        # By default, always include all 24 columns as per spec
        _ = include_paths  # Reserved for future path handling options
        
        # Process rows
        processed_rows = []
        for row in rows:
            # Map raw row to dict
            raw = {
                "item_id": row[0],
                "canonical_id": row[1],
                "doi": row[2],
                "title": row[3],
                "authors_json": row[4],
                "year": row[5],
                "journal": row[6],
                "paper_type": row[7],
                "primary_method": row[8],
                "keywords_json": row[9],
                "in_vf_store": row[10],
                "in_excel_index": row[11],
                "has_chunks": row[12],
                "chunk_count": row[13],
                "has_abstract": row[14],
                "has_introduction": row[15],
                "has_methodology": row[16],
                "has_conclusion": row[17],
                "vf_profile_exists": row[18],
                "vf_chunks_count": row[19],
                "pdf_filename": row[20],
                "chunks_folder": row[21],
                "created_at": row[22],
                "updated_at": row[23],
            }
            
            # Parse JSON fields
            authors = ""
            if raw["authors_json"]:
                try:
                    author_list = json.loads(raw["authors_json"])
                    if isinstance(author_list, list):
                        authors = ", ".join(str(a) for a in author_list)
                except (json.JSONDecodeError, TypeError):
                    authors = str(raw["authors_json"])
            
            keywords = ""
            if raw["keywords_json"]:
                try:
                    keyword_list = json.loads(raw["keywords_json"])
                    if isinstance(keyword_list, list):
                        keywords = ", ".join(str(k) for k in keyword_list)
                except (json.JSONDecodeError, TypeError):
                    keywords = str(raw["keywords_json"])
            
            # Build processed row
            processed = {
                "item_id": raw["item_id"] or "",
                "canonical_id": raw["canonical_id"] or "",
                "doi": raw["doi"] or "",
                "title": raw["title"] or "",
                "authors": authors,
                "year": raw["year"] if raw["year"] else "",
                "journal": raw["journal"] or "",
                "paper_type": raw["paper_type"] or "",
                "primary_method": raw["primary_method"] or "",
                "keywords": keywords,
                "in_vf_store": 1 if raw["in_vf_store"] else 0,
                "in_excel_index": 1 if raw["in_excel_index"] else 0,
                "has_chunks": 1 if raw["has_chunks"] else 0,
                "chunk_count": raw["chunk_count"] if raw["chunk_count"] else 0,
                "has_abstract": 1 if raw["has_abstract"] else 0,
                "has_introduction": 1 if raw["has_introduction"] else 0,
                "has_methodology": 1 if raw["has_methodology"] else 0,
                "has_conclusion": 1 if raw["has_conclusion"] else 0,
                "vf_profile_exists": 1 if raw["vf_profile_exists"] else 0,
                "vf_chunks_count": raw["vf_chunks_count"] if raw["vf_chunks_count"] else 0,
                "pdf_filename": raw["pdf_filename"] or "",
                "chunks_folder": raw["chunks_folder"] or "",
                "created_at": raw["created_at"] or "",
                "updated_at": raw["updated_at"] or "",
            }
            
            processed_rows.append(processed)
        
        # Write output
        if output_format == "json":
            # JSON output
            output_data = [
                {col: row[col] for col in columns}
                for row in processed_rows
            ]
            with open(output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
        else:
            # CSV output with UTF-8 BOM for Excel compatibility
            with open(output, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(processed_rows)
        
        return success_envelope(
            result="ok",
            data={
                "output": output,
                "rows": len(processed_rows),
                "columns": len(columns),
                "format": output_format,
            },
        )
        
    except Exception as e:
        raise CLIBusinessError(
            code="LIBRARY_EXPORT_ERROR",
            message="Failed to export library",
            details=str(e),
        )
