from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import requests

from .types import PaperRecord


@dataclass(frozen=True)
class QdrantSearchResult:
    records: list[PaperRecord]
    collection: str
    source: str = "qdrant"


def _get(collection_url: str) -> requests.Response:
    response = requests.get(collection_url, timeout=8)
    response.raise_for_status()
    return response


def list_points(base_url: str, collection: str, limit: int = 124) -> list[dict[str, Any]]:
    """Scroll points from Qdrant with payload for fallback text search.

    Qdrant `scroll` is enough for small collections (124 docs) and avoids dependency
    on vector-space setup when we only need robust deterministic keyword search.
    """
    url = f"{base_url}/collections/{collection}/points/scroll"
    payload = {
        "limit": limit,
        "with_payload": True,
        "with_vector": False,
    }
    response = requests.post(url, json=payload, timeout=8)
    response.raise_for_status()
    data = response.json()
    return data.get("result", {}).get("points", [])


def _pick(payload: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _normalize(text: str) -> list[str]:
    if not text:
        return []
    cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", text.lower())
    tokens = [t for t in cleaned.split() if len(t) >= 3]
    return tokens


def score_payload(payload: dict[str, Any], query: str) -> float:
    """Simple token-overlap scoring for deterministic fallback ranking."""
    tokens = set(_normalize(query))
    if not tokens:
        return 0.0

    fields = [
        _pick(payload, "title"),
        _pick(payload, "paper_title", "title_en", "Name"),
        _pick(payload, "abstract", "summary", "Abstract"),
        _pick(payload, "keywords", "tags", "Keyword"),
        _pick(payload, "authors", "author", "Author"),
        _pick(payload, "year", "publication_year"),
    ]
    text = " ".join(fields).lower()
    hay = _normalize(text)
    if not hay:
        return 0.0
    return len(set(hay).intersection(tokens)) / max(1, len(tokens))


def to_records(points: list[dict[str, Any]]) -> list[PaperRecord]:
    records: list[PaperRecord] = []
    for point in points:
        payload = point.get("payload") or {}
        pid = str(point.get("id"))
        if not pid:
            pid = payload.get("id") or "unknown"
        records.append(
            PaperRecord(
                paper_id=str(pid),
                title=_pick(payload, "title", "paper_title", "Title", "name"),
                authors=_pick(payload, "authors", "author", "Authors", "author_name"),
                year=str(payload.get("year") or payload.get("publication_year") or ""),
                abstract=_pick(payload, "abstract", "summary", "Abstract"),
                keywords=_pick(payload, "keywords", "tags", "Keyword"),
                source=_pick(payload, "source", "journal", "venue", "publication"),
                doi=_pick(payload, "doi", "DOI"),
                pdf_path=_pick(payload, "pdf_path", "pdf"),
                raw_payload=payload,
            )
        )
    return records


def search_profiles(base_url: str, collection: str, query: str, limit: int = 10) -> QdrantSearchResult:
    points = list_points(base_url, collection, limit=max(200, limit))
    records = to_records(points)

    for record in records:
        score = score_payload(record.raw_payload or {}, query)
        object.__setattr__(record, "relevance", score)

    records.sort(key=lambda r: r.relevance or 0.0, reverse=True)
    return QdrantSearchResult(records=records[:limit], collection=collection)


def get_profile(base_url: str, collection: str, paper_id: str) -> PaperRecord | None:
    points = list_points(base_url, collection, limit=1000)
    for point in points:
        pid = str(point.get("id"))
        payload = point.get("payload") or {}
        if pid == str(paper_id) or str(payload.get("id")) == str(paper_id):
            records = to_records([point])
            return records[0] if records else None
    return None


def validate_collection(base_url: str, collection: str) -> bool:
    try:
        response = _get(f"{base_url}/collections/{collection}")
        return response.status_code == 200
    except Exception:
        return False