from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.qdrant_factory import get_qdrant_client

COLLECTION = "vf_profiles"


class PaperSelector:
    """Select source papers from VF profiles by metadata filters."""

    def __init__(self, collection_name: str = COLLECTION):
        self.collection_name = collection_name
        self.client = get_qdrant_client()

    def select(
        self,
        *,
        paper_ids: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        filters = filters or {}
        selected_ids = {str(x).strip() for x in (paper_ids or []) if str(x).strip()}

        points = self._scroll_meta_points(filters)
        matched: List[Dict[str, Any]] = []

        for p in points:
            payload = p.payload or {}
            pid = str(payload.get("paper_id") or "").strip()
            if not pid:
                continue

            if selected_ids and pid not in selected_ids:
                continue

            meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
            if not self._match_text_filters(meta, filters):
                continue

            matched.append(
                {
                    "paper_id": pid,
                    "title": meta.get("title"),
                    "year": meta.get("year"),
                    "journal": meta.get("journal"),
                    "authors": meta.get("authors") if isinstance(meta.get("authors"), list) else [],
                    "in_library": bool(meta.get("in_library", payload.get("in_library", False))),
                    "source_file": meta.get("source_file"),
                }
            )

        # If user supplied exact paper_ids, keep request order.
        if selected_ids:
            by_id = {m["paper_id"]: m for m in matched}
            ordered = [by_id[pid] for pid in (paper_ids or []) if pid in by_id]
            return ordered

        matched.sort(key=lambda x: (str(x.get("paper_id") or "")))
        return matched

    def _scroll_meta_points(self, filters: Dict[str, Any]) -> List[Any]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue, Range

        must = [FieldCondition(key="chunk_id", match=MatchValue(value="meta"))]

        year_from = filters.get("year_from")
        year_to = filters.get("year_to")
        if year_from is not None or year_to is not None:
            must.append(
                FieldCondition(
                    key="meta.year",
                    range=Range(gte=int(year_from) if year_from is not None else None, lte=int(year_to) if year_to is not None else None),
                )
            )

        if filters.get("in_library") is not None:
            must.append(FieldCondition(key="meta.in_library", match=MatchValue(value=bool(filters.get("in_library")))))

        points: List[Any] = []
        offset = None
        while True:
            batch, offset = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(must=must),
                with_payload=True,
                with_vectors=False,
                limit=256,
                offset=offset,
            )
            if not batch:
                break
            points.extend(batch)
            if offset is None:
                break
        return points

    def _match_text_filters(self, meta: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        def _contains(val: Any, query: str) -> bool:
            q = str(query or "").strip().lower()
            if not q:
                return True
            return q in str(val or "").lower()

        authors_q = filters.get("authors") or []
        if authors_q:
            authors = meta.get("authors") if isinstance(meta.get("authors"), list) else []
            author_text = " ".join(str(a) for a in authors)
            if not all(_contains(author_text, q) for q in authors_q):
                return False

        if filters.get("journal") and not _contains(meta.get("journal"), filters.get("journal")):
            return False

        if filters.get("title") and not _contains(meta.get("title"), filters.get("title")):
            return False

        keywords_q = filters.get("keywords") or []
        if keywords_q:
            kws = []
            for key in ("keywords_author", "keywords_inferred"):
                arr = meta.get(key) if isinstance(meta.get(key), list) else []
                kws.extend(str(x) for x in arr)
            kw_text = " ".join(kws)
            if not all(_contains(kw_text, q) for q in keywords_q):
                return False

        for field in ("volume", "issue", "pages", "paper_type", "primary_method", "empirical_context"):
            if filters.get(field) and not _contains(meta.get(field), filters.get(field)):
                return False

        secondary_q = filters.get("secondary_methods") or []
        if secondary_q:
            secondary = meta.get("secondary_methods") if isinstance(meta.get("secondary_methods"), list) else []
            secondary_text = " ".join(str(x) for x in secondary)
            if not all(_contains(secondary_text, q) for q in secondary_q):
                return False

        return True


def find_paper_md_files(
    library_path: Path | str,
    paper_ids: List[str],
    paper_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Optional[Path]]:
    """Find MD files for given paper_ids.
    
    Args:
        library_path: Path to library directory
        paper_ids: List of paper IDs to find
        paper_metadata: Optional dict mapping paper_id -> {title, authors, year, ...}
                       Used for fuzzy matching when paper_id doesn't match filename
    """
    base = Path(library_path)
    out: Dict[str, Optional[Path]] = {pid: None for pid in paper_ids}
    if not base.exists():
        return out

    files = list(base.rglob("*.md"))

    def _norm(s: str) -> str:
        return "".join(c.lower() for c in s if c.isalnum())

    by_norm = {_norm(f.stem): f for f in files}
    by_name = {f.name: f for f in files}
    paper_metadata = paper_metadata or {}

    for pid in paper_ids:
        meta = paper_metadata.get(pid, {})
        
        # 0. Use source_file if available (most reliable)
        source_file = meta.get("source_file")
        if source_file and source_file in by_name:
            out[pid] = by_name[source_file]
            continue
        
        norm_pid = _norm(pid)
        
        # 1. Exact match
        exact = by_norm.get(norm_pid)
        if exact:
            out[pid] = exact
            continue

        # 2. Substring match (paper_id in filename or vice versa)
        for k, f in by_norm.items():
            if norm_pid and (norm_pid in k or k in norm_pid):
                out[pid] = f
                break
        
        if out[pid]:
            continue
        
        # 3. Match using title (most reliable - titles are unique)
        meta = paper_metadata.get(pid, {})
        title = meta.get("title") or ""
        if title:
            # Extract key words from title (first 5-6 significant words)
            title_words = [w for w in _norm(title).split() if len(w) > 3][:5]
            title_pattern = "".join(title_words)
            if len(title_pattern) >= 15:  # Only if we have enough chars to match
                for k, f in by_norm.items():
                    if title_pattern in k:
                        out[pid] = f
                        break
        
        if out[pid]:
            continue
        
        # 4. Fallback: author + year (less reliable but better than nothing)
        year = meta.get("year")
        authors = meta.get("authors") or []
        first_author = ""
        if isinstance(authors, list) and authors:
            first_author = str(authors[0]).split()[-1]  # Last name
        elif isinstance(authors, str):
            first_author = authors.split()[-1] if authors else ""
        
        if first_author and year:
            search_pattern = _norm(f"{first_author}{year}")
            for k, f in by_norm.items():
                if search_pattern in k:
                    out[pid] = f
                    break

    return out
