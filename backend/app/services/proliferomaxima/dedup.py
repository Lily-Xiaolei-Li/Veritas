from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, Set, Tuple

from app.services.vf_middleware.metadata_index import VFMetadataIndex


class ProliferomaximaDedup:
    def __init__(self, scanned_path: Path | str):
        self.scanned_path = Path(scanned_path)
        self.scanned_path.parent.mkdir(parents=True, exist_ok=True)
        self.index = VFMetadataIndex()
        self.scanned_keys: Set[str] = set()
        self.by_doi: Dict[str, Dict[str, Any]] = {}
        self.by_title_year: Dict[Tuple[str, int | None], Dict[str, Any]] = {}
        self._load_scanned()
        self._load_existing_profiles()

    def _load_scanned(self) -> None:
        if not self.scanned_path.exists():
            self.scanned_keys = set()
            return
        try:
            data = json.loads(self.scanned_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.scanned_keys = set(str(x) for x in data)
            else:
                self.scanned_keys = set(str(x) for x in data.get("keys", []))
        except Exception:
            self.scanned_keys = set()

    def save_scanned(self) -> None:
        payload = {"keys": sorted(self.scanned_keys)}
        self.scanned_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_existing_profiles(self) -> None:
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

    def key_for_ref(self, ref: Dict[str, Any]) -> str:
        doi = (ref.get("doi") or "").strip().lower()
        if doi:
            return f"doi:{doi}"
        title = self._norm_title(ref.get("title"))
        year = ref.get("year")
        token = f"{title}|{year or ''}"
        h = hashlib.sha1(token.encode("utf-8")).hexdigest()
        return f"ty:{h}"

    def is_scanned(self, ref: Dict[str, Any]) -> bool:
        return self.key_for_ref(ref) in self.scanned_keys

    def mark_scanned(self, refs: Iterable[Dict[str, Any]]) -> None:
        for ref in refs:
            self.scanned_keys.add(self.key_for_ref(ref))

    def existing_profile(self, ref: Dict[str, Any]) -> Dict[str, Any] | None:
        doi = (ref.get("doi") or "").strip().lower()
        if doi and doi in self.by_doi:
            return self.by_doi[doi]

        key = (self._norm_title(ref.get("title")), ref.get("year"))
        return self.by_title_year.get(key)

    @staticmethod
    def _norm_title(text: Any) -> str:
        s = str(text or "").lower().strip()
        return " ".join(s.split())
