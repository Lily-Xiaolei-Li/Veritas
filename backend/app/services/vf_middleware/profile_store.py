from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# Namespace UUID for deterministic point ID generation
_VF_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")


def _point_uuid(paper_id: str, chunk_id: str) -> str:
    """Deterministic UUID from paper_id:chunk_id (Qdrant requires UUID or int)."""
    return str(uuid.uuid5(_VF_NAMESPACE, f"{paper_id}:{chunk_id}"))

from app.logging_config import get_logger

logger = get_logger("vf_middleware.profile_store")

DEFAULT_QDRANT_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\qdrant_data")
DEFAULT_COLLECTION = "vf_profiles"
CHUNK_ORDER = [
    "meta",
    "abstract",
    "theory",
    "literature",
    "research_questions",
    "contributions",
    "key_concepts",
    "cited_for",
]

import threading

_model = None
_encode_lock = threading.Lock()


def _get_model():
    global _model
    if _model is not None:
        return _model

    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer("BAAI/bge-m3")
    return _model


def _safe_encode(texts):
    """Thread-safe encoding with lock to prevent concurrent BGE-M3 access."""
    model = _get_model()
    with _encode_lock:
        if isinstance(texts, str):
            return model.encode(texts).tolist()
        return model.encode(texts, batch_size=8, show_progress_bar=False).tolist()


class VFProfileStore:
    def __init__(self, qdrant_path: Path | str = DEFAULT_QDRANT_PATH, collection_name: str = DEFAULT_COLLECTION):
        from app.services.qdrant_factory import get_qdrant_client

        self.qdrant_path = Path(qdrant_path)
        self.collection_name = collection_name
        self.client = get_qdrant_client()

    def ensure_collection(self) -> None:
        from qdrant_client.http.models import Distance, VectorParams

        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if exists:
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )

    def upsert_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        from qdrant_client.models import PointStruct

        self.ensure_collection()

        paper_id = profile["paper_id"]
        in_library = bool(profile.get("in_library", False))
        source_type = profile.get("source_type", "library" if in_library else "external")
        chunks = profile.get("chunks", {})

        ids: List[str] = []
        points: List[PointStruct] = []

        # Collect all texts first, then batch encode with lock
        text_list = []
        for chunk_id in CHUNK_ORDER:
            text = chunks.get(chunk_id, "")
            if chunk_id == "meta" and isinstance(text, dict):
                text = json.dumps(text, ensure_ascii=False)
            if text is None:
                text = ""
            text_list.append(str(text))

        # Single locked batch encode for all 8 chunks
        vectors = _safe_encode(text_list)

        for idx, chunk_id in enumerate(CHUNK_ORDER, start=1):
            text = text_list[idx - 1]
            vec = vectors[idx - 1]
            vector = vec if isinstance(vec, list) else vec.tolist()
            point_id = _point_uuid(paper_id, chunk_id)
            ids.append(f"{paper_id}:{chunk_id}")

            payload = {
                "paper_id": paper_id,
                "chunk_id": chunk_id,
                "chunk_index": idx,
                "in_library": in_library,
                "source_type": source_type,
                "text": text,
                "meta": profile.get("meta", {}),
            }
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        self.client.upsert(collection_name=self.collection_name, points=points)
        return {"paper_id": paper_id, "chunks_upserted": len(points), "point_ids": ids}

    def get_profile(self, paper_id: str) -> Optional[Dict[str, Any]]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        self.ensure_collection()
        response = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=[FieldCondition(key="paper_id", match=MatchValue(value=paper_id))]
            ),
            with_payload=True,
            limit=20,
        )

        points = response[0]
        if not points:
            return None

        chunks: Dict[str, str] = {}
        meta: Dict[str, Any] = {}
        in_library = False
        source_type = "external"

        for p in points:
            payload = p.payload or {}
            chunk_id = str(payload.get("chunk_id", ""))
            if chunk_id:
                chunks[chunk_id] = str(payload.get("text", ""))
            if not meta and isinstance(payload.get("meta"), dict):
                meta = payload["meta"]
            in_library = bool(payload.get("in_library", in_library))
            source_type = str(payload.get("source_type", source_type))

        if "meta" in chunks and not meta:
            try:
                meta = json.loads(chunks["meta"])
            except Exception:
                meta = {}

        return {
            "paper_id": paper_id,
            "in_library": in_library,
            "source_type": source_type,
            "meta": meta,
            "chunks": chunks,
        }

    def semantic_search(self, query: str, limit: int = 8, chunk_id: Optional[str] = None) -> List[Dict[str, Any]]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        self.ensure_collection()
        query_vector = _safe_encode(query)

        q_filter = None
        if chunk_id:
            q_filter = Filter(must=[FieldCondition(key="chunk_id", match=MatchValue(value=chunk_id))])

        resp = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
            query_filter=q_filter,
        )

        out: List[Dict[str, Any]] = []
        for point in resp.points:
            payload = point.payload or {}
            out.append(
                {
                    "paper_id": payload.get("paper_id"),
                    "chunk_id": payload.get("chunk_id"),
                    "chunk_index": payload.get("chunk_index"),
                    "score": point.score,
                    "text": payload.get("text", ""),
                    "in_library": payload.get("in_library", False),
                    "source_type": payload.get("source_type", "external"),
                    "meta": payload.get("meta", {}),
                }
            )
        return out

    def delete_profile(self, paper_id: str) -> Dict[str, Any]:
        from qdrant_client.models import Filter, FieldCondition, MatchValue, PointIdsList

        profile = self.get_profile(paper_id)
        if not profile:
            return {"paper_id": paper_id, "deleted": 0}

        ids = [_point_uuid(paper_id, chunk_id) for chunk_id in CHUNK_ORDER if chunk_id in profile.get("chunks", {})]
        if ids:
            self.client.delete(collection_name=self.collection_name, points_selector=PointIdsList(points=ids))

        return {"paper_id": paper_id, "deleted": len(ids)}

    def list_profiles(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        self.ensure_collection()
        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            with_payload=True,
            limit=max(limit * 8, 8),
            offset=offset,
        )

        by_paper: Dict[str, Dict[str, Any]] = {}
        for p in points:
            payload = p.payload or {}
            paper_id = str(payload.get("paper_id", ""))
            if not paper_id:
                continue
            if paper_id not in by_paper:
                by_paper[paper_id] = {
                    "paper_id": paper_id,
                    "in_library": payload.get("in_library", False),
                    "source_type": payload.get("source_type", "external"),
                    "title": (payload.get("meta") or {}).get("title"),
                    "year": (payload.get("meta") or {}).get("year"),
                    "authors": (payload.get("meta") or {}).get("authors", []),
                    "chunks": 0,
                }
            by_paper[paper_id]["chunks"] += 1

        return list(by_paper.values())[:limit]

    def stats(self) -> Dict[str, Any]:
        self.ensure_collection()
        info = self.client.get_collection(self.collection_name)
        count = self.client.count(collection_name=self.collection_name, exact=True).count
        return {
            "collection": self.collection_name,
            "vectors": count,
            "points_count": info.points_count,
            "segments_count": info.segments_count,
            "vector_size": 1024,
        }
