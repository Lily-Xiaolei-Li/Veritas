from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

from app.logging_config import get_logger

from .api_resolver import ProliferomaximaAPIResolver
from .dedup import ProliferomaximaDedup
from .ref_extractor import ReferenceExtractor

logger = get_logger("proliferomaxima.batch")

DEFAULT_LIBRARY_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")
DEFAULT_SCANNED_PATH = Path(__file__).resolve().parents[3] / "data" / "proliferomaxima_scanned.json"
DEFAULT_SKIPPED_PATH = Path(__file__).resolve().parents[3] / "data" / "proliferomaxima_skipped.json"


class ProliferomaximaBatchEngine:
    def __init__(
        self,
        *,
        library_path: Path | str = DEFAULT_LIBRARY_PATH,
        scanned_path: Path | str = DEFAULT_SCANNED_PATH,
        skipped_path: Path | str = DEFAULT_SKIPPED_PATH,
        api_base_url: Optional[str] = None,
    ):
        self.library_path = Path(library_path)
        self.scanned_path = Path(scanned_path)
        self.skipped_path = Path(skipped_path)
        self.skipped_path.parent.mkdir(parents=True, exist_ok=True)

        self.extractor = ReferenceExtractor(self.library_path)
        self.dedup = ProliferomaximaDedup(self.scanned_path)
        self.resolver = ProliferomaximaAPIResolver()
        self.api_base_url = api_base_url or os.getenv("AGENTB_API_URL", "http://localhost:8001")

    async def run(
        self,
        *,
        max_files: Optional[int] = None,
        max_items: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        refs = self.extractor.extract_all(max_files=max_files)
        if max_items is not None:
            refs = refs[: max(0, int(max_items))]

        total = len(refs)
        added = skipped = failed = duplicates = 0
        skipped_records: List[Dict[str, Any]] = []
        processed_for_scan: List[Dict[str, Any]] = []

        for idx, ref in enumerate(refs, start=1):
            if progress_callback:
                await progress_callback(idx - 1, total, "dedup+resolve")

            if self.dedup.is_scanned(ref):
                duplicates += 1
                continue

            existing = self.dedup.existing_profile(ref)
            if existing:
                meta = existing.get("meta") or {}
                if bool(meta.get("full_article", False)):
                    skipped += 1
                    skipped_records.append({"reason": "existing_full_article", "ref": ref})
                else:
                    skipped += 1
                    skipped_records.append({"reason": "existing_profile", "ref": ref})
                processed_for_scan.append(ref)
                continue

            resolved = await self.resolver.resolve(ref)
            if not resolved or not str(resolved.get("abstract") or "").strip():
                skipped += 1
                skipped_records.append({"reason": "no_abstract", "ref": ref, "resolved": resolved})
                processed_for_scan.append(ref)
                continue

            metadata = {
                "title": resolved.get("title") or ref.get("title"),
                "authors": resolved.get("authors") or ref.get("authors") or [],
                "year": resolved.get("year") or ref.get("year"),
                "doi": (resolved.get("doi") or ref.get("doi") or "").lower() or None,
                "journal": resolved.get("journal"),
                "full_article": False,
                "confidence": "inferred",
                "source_spell": "proliferomaxima",
                "inferred_from": "abstract",
                "cited_by": [ref.get("source_paper")],
            }

            paper_id = self._build_paper_id(metadata)
            ok = await self._generate_vf_profile(paper_id=paper_id, metadata=metadata, abstract=str(resolved.get("abstract") or ""))
            processed_for_scan.append(ref)

            if ok:
                added += 1
            else:
                failed += 1
                skipped_records.append({"reason": "vf_generate_failed", "ref": ref, "resolved": resolved})

        self.dedup.mark_scanned(processed_for_scan)
        self.dedup.save_scanned()
        self._append_skipped(skipped_records)

        if progress_callback:
            await progress_callback(total, total, "done")

        return {
            "total_refs": total,
            "added": added,
            "skipped": skipped,
            "failed": failed,
            "duplicates": duplicates,
            "skipped_records": skipped_records[-200:],
        }

    async def _generate_vf_profile(self, *, paper_id: str, metadata: Dict[str, Any], abstract: str) -> bool:
        payload = {
            "paper_id": paper_id,
            "metadata": metadata,
            "abstract": abstract,
            "full_text": None,
            "in_library": False,
            "agent": "helper",
        }

        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                r = await client.post(f"{self.api_base_url}/api/v1/vf/generate", json=payload)
                return r.status_code in (200, 201)
        except Exception as exc:
            logger.error(f"VF generate failed for {paper_id}: {exc}")
            return False

    def _append_skipped(self, records: List[Dict[str, Any]]) -> None:
        if not records:
            return

        existing: List[Dict[str, Any]] = []
        if self.skipped_path.exists():
            try:
                existing = json.loads(self.skipped_path.read_text(encoding="utf-8"))
                if not isinstance(existing, list):
                    existing = []
            except Exception:
                existing = []

        existing.extend(records)
        self.skipped_path.write_text(json.dumps(existing[-5000:], ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_paper_id(self, meta: Dict[str, Any]) -> str:
        doi = str(meta.get("doi") or "").strip().lower()
        if doi:
            safe = "".join(c if c.isalnum() else "_" for c in doi)
            return f"doi_{safe[:120]}"

        title = str(meta.get("title") or "untitled").lower().strip()
        year = str(meta.get("year") or "0000")
        digest = hashlib.sha1(f"{title}|{year}".encode("utf-8")).hexdigest()[:12]
        base = "_".join(title.split()[:6])
        base = "".join(c if c.isalnum() or c == "_" else "_" for c in base).strip("_") or "untitled"
        return f"ref_{year}_{base[:60]}_{digest}"
