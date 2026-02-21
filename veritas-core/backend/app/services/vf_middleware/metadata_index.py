from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_INDEX_PATH = Path(__file__).resolve().parents[3] / "data" / "vf_metadata.sqlite"


class VFMetadataIndex:
    """Fast exact-lookup index for paper metadata."""

    def __init__(self, db_path: Path | str = DEFAULT_INDEX_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vf_profiles_index (
                    paper_id TEXT PRIMARY KEY,
                    authors_json TEXT NOT NULL,
                    year INTEGER,
                    title TEXT,
                    in_library INTEGER NOT NULL DEFAULT 0,
                    profile_exists INTEGER NOT NULL DEFAULT 1,
                    chunks_generated INTEGER NOT NULL DEFAULT 8,
                    last_updated TEXT NOT NULL,
                    meta_json TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vf_year ON vf_profiles_index(year)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vf_title ON vf_profiles_index(title)")
            conn.commit()

    def upsert(self, paper_id: str, meta: Dict[str, Any], chunks_generated: int = 8) -> Dict[str, Any]:
        authors = meta.get("authors") if isinstance(meta.get("authors"), list) else []
        year = meta.get("year")
        try:
            year = int(year) if year is not None else None
        except Exception:
            year = None

        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO vf_profiles_index(
                    paper_id, authors_json, year, title, in_library,
                    profile_exists, chunks_generated, last_updated, meta_json
                ) VALUES(?, ?, ?, ?, ?, 1, ?, ?, ?)
                ON CONFLICT(paper_id) DO UPDATE SET
                    authors_json=excluded.authors_json,
                    year=excluded.year,
                    title=excluded.title,
                    in_library=excluded.in_library,
                    profile_exists=1,
                    chunks_generated=excluded.chunks_generated,
                    last_updated=excluded.last_updated,
                    meta_json=excluded.meta_json
                """,
                (
                    paper_id,
                    json.dumps(authors, ensure_ascii=False),
                    year,
                    meta.get("title"),
                    1 if bool(meta.get("in_library", False)) else 0,
                    chunks_generated,
                    now,
                    json.dumps(meta, ensure_ascii=False),
                ),
            )
            conn.commit()

        return {"paper_id": paper_id, "updated": True}

    def get(self, paper_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM vf_profiles_index WHERE paper_id=?", (paper_id,)).fetchone()

        if not row:
            return None
        return self._row_to_dict(row)

    def exact_lookup(self, author: str, year: int) -> List[Dict[str, Any]]:
        norm_author = author.lower().strip()
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM vf_profiles_index WHERE year=?", (int(year),)).fetchall()

        matches: List[Dict[str, Any]] = []
        for row in rows:
            authors = json.loads(row["authors_json"] or "[]")
            if any(norm_author in str(a).lower() for a in authors):
                matches.append(self._row_to_dict(row))
        return matches

    def list(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM vf_profiles_index ORDER BY last_updated DESC LIMIT ? OFFSET ?",
                (int(limit), int(offset)),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def delete(self, paper_id: str) -> Dict[str, Any]:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM vf_profiles_index WHERE paper_id=?", (paper_id,))
            conn.commit()
        return {"paper_id": paper_id, "deleted": cur.rowcount}

    def stats(self) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN in_library=1 THEN 1 ELSE 0 END) as in_library,
                    SUM(CASE WHEN in_library=0 THEN 1 ELSE 0 END) as external
                FROM vf_profiles_index
                """
            ).fetchone()
        return {
            "total_profiles": int(row["total"] or 0),
            "in_library_profiles": int(row["in_library"] or 0),
            "external_profiles": int(row["external"] or 0),
        }

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "paper_id": row["paper_id"],
            "authors": json.loads(row["authors_json"] or "[]"),
            "year": row["year"],
            "title": row["title"],
            "in_library": bool(row["in_library"]),
            "profile_exists": bool(row["profile_exists"]),
            "chunks_generated": row["chunks_generated"],
            "last_updated": row["last_updated"],
            "meta": json.loads(row["meta_json"] or "{}"),
        }
