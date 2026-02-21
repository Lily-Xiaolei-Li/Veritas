from __future__ import annotations

from typing import Any, Dict, Tuple

from app.services.vf_middleware.metadata_index import VFMetadataIndex


class ProliferomaximaDedup:
    """
    Deduplication against VF Store (source of truth).
    No temporary files - queries Qdrant directly.
    """

    def __init__(self):
        self.index = VFMetadataIndex()
        self.by_doi: Dict[str, Dict[str, Any]] = {}
        self.by_title_year: Dict[Tuple[str, int | None], Dict[str, Any]] = {}
        self._load_existing_profiles()

    def _load_existing_profiles(self) -> None:
        """Load all existing VF profiles from Qdrant for fast lookup."""
        rows = self.index.list(limit=300000, offset=0)
        for row in rows:
            meta = row.get("meta") or {}
            doi = str(meta.get("doi") or "").strip().lower()
            if doi:
                self.by_doi[doi] = row
            title_key = self._norm_title(meta.get("title"))
            year = meta.get("year") if isinstance(meta, dict) else None
            if title_key:
                self.by_title_year[(title_key, year)] = row

    def refresh(self) -> None:
        """Refresh the cache from VF Store."""
        self.by_doi.clear()
        self.by_title_year.clear()
        self._load_existing_profiles()

    def existing_profile(self, ref: Dict[str, Any]) -> Dict[str, Any] | None:
        """Check if reference already has a VF profile in the store."""
        # Try DOI match first (most reliable)
        doi = (ref.get("doi") or "").strip().lower()
        if doi and doi in self.by_doi:
            return self.by_doi[doi]

        # Fall back to title + year match
        key = (self._norm_title(ref.get("title")), ref.get("year"))
        return self.by_title_year.get(key)

    def register_new(self, ref: Dict[str, Any], profile: Dict[str, Any]) -> None:
        """Register a newly created profile in the cache (avoid re-querying Qdrant)."""
        doi = (ref.get("doi") or "").strip().lower()
        if doi:
            self.by_doi[doi] = profile
        title_key = self._norm_title(ref.get("title"))
        year = ref.get("year")
        if title_key:
            self.by_title_year[(title_key, year)] = profile

    @staticmethod
    def _norm_title(text: Any) -> str:
        s = str(text or "").lower().strip()
        return " ".join(s.split())
