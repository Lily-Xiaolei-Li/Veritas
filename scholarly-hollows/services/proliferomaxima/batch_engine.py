from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

import httpx

from app.logging_config import get_logger
from app.services.qdrant_factory import get_qdrant_client

from .api_resolver import ProliferomaximaAPIResolver
from .dedup import ProliferomaximaDedup
from .paper_selector import find_paper_md_files
from .ref_extractor import ReferenceExtractor
from .ref_normalizer import ReferenceNormalizer

logger = get_logger("proliferomaxima.batch")

DEFAULT_LIBRARY_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")
DEFAULT_SKIPPED_PATH = Path(__file__).resolve().parents[3] / "data" / "proliferomaxima_skipped.json"
DEFAULT_NEEDS_REVIEW_PATH = Path(__file__).resolve().parents[3] / "data" / "proliferomaxima_needs_review.json"
DEFAULT_COLLECTION = "vf_profiles"

# Reference type categories
ALL_REFERENCE_TYPES = {"journal_article", "book", "book_chapter", "conference", "thesis", "report", "webpage", "other"}
DEFAULT_ACADEMIC_TYPES = {"journal_article", "book", "book_chapter", "conference", "thesis"}


class ProliferomaximaBatchEngine:
    def __init__(
        self,
        *,
        library_path: Path | str = DEFAULT_LIBRARY_PATH,
        skipped_path: Path | str = DEFAULT_SKIPPED_PATH,
        api_base_url: Optional[str] = None,
    ):
        self.library_path = Path(library_path)
        self.skipped_path = Path(skipped_path)
        self.skipped_path.parent.mkdir(parents=True, exist_ok=True)

        self.extractor = ReferenceExtractor(self.library_path)
        self.normalizer = ReferenceNormalizer()
        self.dedup = ProliferomaximaDedup()  # Now queries VF Store directly
        self.resolver = ProliferomaximaAPIResolver()
        self.api_base_url = api_base_url or os.getenv("AGENTB_API_URL", "http://localhost:8001")
        self.qdrant = get_qdrant_client()

    async def run(
        self,
        *,
        max_files: Optional[int] = None,
        max_items: Optional[int] = None,
        reference_types: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        refs = self.extractor.extract_all(max_files=max_files)
        if max_items is not None:
            refs = refs[: max(0, int(max_items))]
        return await self._process_refs(
            refs=refs,
            progress_callback=progress_callback,
            reference_types=reference_types,
            year_from=year_from,
            year_to=year_to,
        )

    async def run_by_papers(
        self,
        *,
        paper_ids: List[str],
        paper_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
        max_refs_per_paper: Optional[int] = None,
        max_total: Optional[int] = None,
        require_abstract: bool = True,
        min_ref_year: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        paper_ids = [str(pid).strip() for pid in paper_ids if str(pid).strip()]
        if not paper_ids:
            return {
                "total_refs": 0,
                "added": 0,
                "already_exists": 0,
                "needs_review": 0,
                "failed": 0,
                "needs_review_records": [],
                "skipped_records": [],
                "selected_papers": [],
                "cite_how_updates": [],
            }

        refs: List[Dict[str, Any]] = []
        cite_how_updates: List[Dict[str, Any]] = []
        file_map = find_paper_md_files(self.library_path, paper_ids, paper_metadata=paper_metadata)

        for pid in paper_ids:
            per_paper_cap = max(0, int(max_refs_per_paper)) if max_refs_per_paper is not None else None
            file_path = file_map.get(pid)
            source_key = file_path.name if file_path else pid

            # Priority 1: AI-normalize markdown full text references when available.
            if file_path and file_path.exists():
                raw_section = self.extractor.extract_raw_reference_section(file_path)
                if raw_section:
                    normalized = await self.normalizer.normalize_references(
                        raw_text=raw_section,
                        source_paper=file_path.name,
                        max_refs=(per_paper_cap if per_paper_cap is not None else 100),
                    )

                    for item in normalized:
                        structured = item.get("structured") if isinstance(item.get("structured"), dict) else {}
                        refs.append(
                            {
                                "raw_text": str(item.get("raw_text") or item.get("cite_how", {}).get("full_ref") or ""),
                                "title": structured.get("title") or "",
                                "authors": structured.get("authors") if isinstance(structured.get("authors"), list) else [],
                                "year": structured.get("year") if isinstance(structured.get("year"), int) else None,
                                "doi": (str(structured.get("doi")).lower() if structured.get("doi") else None),
                                "journal": structured.get("journal"),
                                "type": structured.get("type") or "other",
                                "cited_for": None,
                                "source_paper": file_path.name,
                                "cite_how": item.get("cite_how") if isinstance(item.get("cite_how"), dict) else {},
                                "corrupted": bool(item.get("corrupted", False)),
                            }
                        )

                    cite_how_list = [r.get("cite_how") for r in refs if r.get("source_paper") == file_path.name and isinstance(r.get("cite_how"), dict)]
                    updated = self._update_profile_cite_how(pid, cite_how_list)
                    cite_how_updates.append(
                        {
                            "paper_id": pid,
                            "source_paper": file_path.name,
                            "updated": updated,
                            "count": len(cite_how_list),
                        }
                    )

            # Priority 2: supplement with VF `cited_for` mentions.
            if per_paper_cap is None or len([r for r in refs if str(r.get("source_paper")) == source_key]) < per_paper_cap:
                cited_for_text = self._get_chunk_text(pid, "cited_for")
                if cited_for_text:
                    remaining = None
                    if per_paper_cap is not None:
                        existing_count = len([r for r in refs if str(r.get("source_paper")) == source_key])
                        remaining = max(per_paper_cap - existing_count, 0)
                    refs.extend(self.extractor.extract_from_text_mentions(cited_for_text, source_paper=source_key, max_refs=remaining))

            # Abstract-only profile with no .md: we intentionally skip full ref extraction.

        if min_ref_year is not None:
            refs = [r for r in refs if not isinstance(r.get("year"), int) or int(r.get("year")) >= int(min_ref_year)]

        if max_total is not None:
            refs = refs[: max(0, int(max_total))]

        result = await self._process_refs(refs=refs, progress_callback=progress_callback, require_abstract=require_abstract, selected_papers=paper_ids)
        result["cite_how_updates"] = cite_how_updates
        return result

    async def _process_refs(
        self,
        *,
        refs: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], Awaitable[None]]] = None,
        require_abstract: bool = True,
        selected_papers: Optional[List[str]] = None,
        reference_types: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> Dict[str, Any]:
        total = len(refs)
        added = failed = already_exists = 0
        skipped_non_academic = 0
        skipped_year_filter = 0
        skipped_records: List[Dict[str, Any]] = []
        needs_review: List[Dict[str, Any]] = []  # Papers without abstract for user review

        # Determine allowed reference types (default to academic types if not specified)
        allowed_types = set(reference_types) if reference_types else DEFAULT_ACADEMIC_TYPES

        for idx, ref in enumerate(refs, start=1):
            # Filter by reference type
            ref_type = ref.get("type", "other")
            if ref_type not in allowed_types:
                skipped_non_academic += 1
                skipped_records.append({"reason": "filtered_type", "type": ref_type, "ref": ref})
                continue

            # Filter by year range
            ref_year = ref.get("year")
            if isinstance(ref_year, int):
                if year_from is not None and ref_year < year_from:
                    skipped_year_filter += 1
                    skipped_records.append({"reason": "year_too_old", "year": ref_year, "ref": ref})
                    continue
                if year_to is not None and ref_year > year_to:
                    skipped_year_filter += 1
                    skipped_records.append({"reason": "year_too_new", "year": ref_year, "ref": ref})
                    continue
            if progress_callback:
                await progress_callback(idx - 1, total, "check+resolve")

            # Check VF Store directly (source of truth)
            existing = self.dedup.existing_profile(ref)
            if existing:
                meta = existing.get("meta") or {}
                already_exists += 1
                if bool(meta.get("full_article", False)):
                    skipped_records.append({"reason": "existing_full_article", "ref": ref})
                else:
                    skipped_records.append({"reason": "existing_profile", "ref": ref})
                continue

            # Resolve metadata from APIs (CrossRef → Semantic Scholar → OpenAlex)
            resolved = await self.resolver.resolve(ref)
            if require_abstract and (not resolved or not str(resolved.get("abstract") or "").strip()):
                # Save for user review instead of just skipping
                needs_review.append({
                    "title": (resolved or {}).get("title") or ref.get("title"),
                    "authors": (resolved or {}).get("authors") or ref.get("authors") or [],
                    "year": (resolved or {}).get("year") or ref.get("year"),
                    "doi": (resolved or {}).get("doi") or ref.get("doi"),
                    "journal": (resolved or {}).get("journal") or ref.get("journal"),
                    "type": ref.get("type"),
                    "source_paper": ref.get("source_paper"),
                    "raw_text": ref.get("raw_text"),
                    "reason": "no_abstract_available",
                    "apis_checked": ["crossref", "semanticscholar", "openalex"],
                })
                continue

            metadata = {
                "title": (resolved or {}).get("title") or ref.get("title"),
                "authors": (resolved or {}).get("authors") or ref.get("authors") or [],
                "year": (resolved or {}).get("year") or ref.get("year"),
                "doi": ((resolved or {}).get("doi") or ref.get("doi") or "").lower() or None,
                "journal": (resolved or {}).get("journal"),
                "full_article": False,
                "confidence": "inferred",
                "source_spell": "proliferomaxima",
                "inferred_from": "abstract",
                "abstract_source": (resolved or {}).get("source", "unknown"),
                "cited_by": [ref.get("source_paper")],
            }

            paper_id = self._build_paper_id(metadata)
            ok = await self._generate_vf_profile(
                paper_id=paper_id,
                metadata=metadata,
                abstract=str((resolved or {}).get("abstract") or ""),
            )

            if ok:
                added += 1
                # Register in cache so we don't re-process within same batch
                self.dedup.register_new(ref, {"meta": metadata})
            else:
                failed += 1
                skipped_records.append({"reason": "vf_generate_failed", "ref": ref, "resolved": resolved})

        # Save needs_review as artifact
        if needs_review:
            self._save_needs_review(needs_review, selected_papers)

        self._append_skipped(skipped_records)

        if progress_callback:
            await progress_callback(total, total, "done")

        return {
            "total_refs": total,
            "added": added,
            "already_exists": already_exists,
            "needs_review": len(needs_review),
            "skipped_non_academic": skipped_non_academic,
            "skipped_year_filter": skipped_year_filter,
            "failed": failed,
            "needs_review_records": needs_review,
            "skipped_records": skipped_records[-200:],
            "selected_papers": selected_papers or [],
            "filters_applied": {
                "reference_types": list(allowed_types),
                "year_from": year_from,
                "year_to": year_to,
            },
        }

    def _get_chunk_text(self, paper_id: str, chunk_id: str) -> str:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        points, _ = self.qdrant.scroll(
            collection_name=DEFAULT_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(key="paper_id", match=MatchValue(value=paper_id)),
                    FieldCondition(key="chunk_id", match=MatchValue(value=chunk_id)),
                ]
            ),
            with_payload=True,
            with_vectors=False,
            limit=1,
        )
        if not points:
            return ""
        payload = points[0].payload or {}
        return str(payload.get("text") or "")

    def _update_profile_cite_how(self, paper_id: str, cite_how: List[Dict[str, Any]]) -> bool:
        """Append cite_how field to existing meta chunk payload for a source paper."""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        try:
            points, _ = self.qdrant.scroll(
                collection_name=DEFAULT_COLLECTION,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(key="paper_id", match=MatchValue(value=paper_id)),
                        FieldCondition(key="chunk_id", match=MatchValue(value="meta")),
                    ]
                ),
                with_payload=True,
                with_vectors=False,
                limit=1,
            )
            if not points:
                return False

            point = points[0]
            payload = dict(point.payload or {})
            payload["cite_how"] = cite_how

            # Keep nested meta mirror in sync for consumers that read payload.meta
            meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
            meta = dict(meta)
            meta["cite_how"] = cite_how
            payload["meta"] = meta

            self.qdrant.set_payload(
                collection_name=DEFAULT_COLLECTION,
                payload=payload,
                points=[point.id],
            )
            return True
        except Exception as exc:
            logger.warning(f"Failed to update cite_how for {paper_id}: {exc}")
            return False

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

    def _save_needs_review(self, records: List[Dict[str, Any]], selected_papers: Optional[List[str]] = None) -> None:
        """Save papers without abstract as artifact for user review."""
        import time
        artifact = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "source_papers": selected_papers or [],
            "count": len(records),
            "description": "References that could not be proliferated (no abstract found in CrossRef, Semantic Scholar, or OpenAlex). Review manually if needed.",
            "items": records,
        }
        DEFAULT_NEEDS_REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
        DEFAULT_NEEDS_REVIEW_PATH.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8"
        )
        logger.info(f"Saved {len(records)} items for review to {DEFAULT_NEEDS_REVIEW_PATH}")

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
