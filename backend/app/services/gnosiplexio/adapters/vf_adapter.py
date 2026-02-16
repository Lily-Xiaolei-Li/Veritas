"""VF Store adapter — reads data from existing Qdrant VF profiles and metadata index."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.services.vf_middleware.metadata_index import VFMetadataIndex
from app.services.vf_middleware.profile_store import VFProfileStore

from . import Citation, SearchResult, WorkRecord

logger = get_logger("gnosiplexio.adapters.vf")


class VFAdapter:
    """Reads academic works from the VF profile store and metadata index."""

    def __init__(
        self,
        profile_store: VFProfileStore | None = None,
        metadata_index: VFMetadataIndex | None = None,
    ) -> None:
        self.profiles = profile_store or VFProfileStore()
        self.meta_idx = metadata_index or VFMetadataIndex()

    def list_works(self) -> List[WorkRecord]:
        """List all papers in the metadata index."""
        rows = self.meta_idx.list(limit=10_000)
        return [
            WorkRecord(
                id=r["paper_id"],
                title=r.get("title") or "",
                authors=r.get("authors", []),
                year=r.get("year"),
                doi=r.get("meta", {}).get("doi"),
                type=r.get("meta", {}).get("type", "unknown"),
            )
            for r in rows
        ]

    def get_profile(self, work_id: str) -> Optional[Dict[str, Any]]:
        """Fetch the full VF profile (all chunks) from Qdrant."""
        return self.profiles.get_profile(work_id)

    def get_citations(self, work_id: str) -> List[Citation]:
        """Extract citation relations from the 'cited_for' chunk of a VF profile."""
        profile = self.profiles.get_profile(work_id)
        if not profile:
            return []

        cited_for_text = profile.get("chunks", {}).get("cited_for", "")
        if not cited_for_text:
            return []

        return self._parse_cited_for(work_id, cited_for_text)

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """Semantic search via Qdrant over VF profile chunks."""
        hits = self.profiles.semantic_search(query, limit=top_k, chunk_id="abstract")
        seen: set[str] = set()
        results: List[SearchResult] = []
        for h in hits:
            pid = h.get("paper_id", "")
            if pid in seen:
                continue
            seen.add(pid)
            results.append(
                SearchResult(
                    work_id=pid,
                    title=h.get("meta", {}).get("title", ""),
                    score=float(h.get("score", 0.0)),
                )
            )
        return results

    # ── private ────────────────────────────────────────────────────

    @staticmethod
    def _parse_cited_for(work_id: str, text: str) -> List[Citation]:
        """Parse the cited_for chunk text into Citation dicts.

        Expected format per line: ``<cited_id> — <cited_for_reason>``
        or JSON list.
        """
        citations: List[Citation] = []
        # Try JSON first
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for item in data:
                    citations.append(
                        Citation(
                            citing_id=work_id,
                            cited_id=str(item.get("id", item.get("cited_id", ""))),
                            context=str(item.get("context", "")),
                            cited_for=str(item.get("cited_for", item.get("reason", ""))),
                        )
                    )
                return citations
        except (json.JSONDecodeError, TypeError):
            pass

        # Fallback: line-based parsing
        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if "—" in line:
                parts = line.split("—", 1)
            elif " - " in line:
                parts = line.split(" - ", 1)
            else:
                continue
            cited_id = parts[0].strip()
            reason = parts[1].strip() if len(parts) > 1 else ""
            citations.append(
                Citation(citing_id=work_id, cited_id=cited_id, context="", cited_for=reason)
            )
        return citations
