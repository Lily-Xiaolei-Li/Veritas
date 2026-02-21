from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.logging_config import get_logger
from app.services.vf_middleware.metadata_index import VFMetadataIndex
from app.services.vf_middleware.profile_generator import VFProfileGenerator, list_available_agents
from app.services.vf_middleware.profile_store import VFProfileStore

logger = get_logger("vf_middleware.routes")

router = APIRouter(prefix="/vf", tags=["vf_middleware"])

_generator: VFProfileGenerator | None = None
_store: VFProfileStore | None = None
_index: VFMetadataIndex | None = None

DEFAULT_LIBRARY_PATH = Path(r"C:\Users\Barry Li (UoN)\clawd\projects\library-rag\data\parsed")


def _get_generator() -> VFProfileGenerator:
    global _generator
    if _generator is None:
        _generator = VFProfileGenerator()
    return _generator


def _get_store() -> VFProfileStore:
    global _store
    if _store is None:
        _store = VFProfileStore()
    return _store


def _get_index() -> VFMetadataIndex:
    global _index
    if _index is None:
        _index = VFMetadataIndex()
    return _index


class VFGenerateRequest(BaseModel):
    paper_id: str = Field(..., min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    abstract: str = Field(default="")
    full_text: Optional[str] = None
    in_library: bool = True
    agent: str = "helper"


class VFGenerateResponse(BaseModel):
    paper_id: str
    chunks_upserted: int
    in_library: bool
    source_type: str


class VFBatchRequest(BaseModel):
    items: List[VFGenerateRequest]


class VFSyncRequest(BaseModel):
    library_path: Optional[str] = None
    agent: str = "helper"
    dry_run: bool = False


@router.get("/agents")
async def vf_agents():
    return {"agents": list_available_agents()}


@router.post("/generate", response_model=VFGenerateResponse)
async def vf_generate(req: VFGenerateRequest):
    try:
        profile = await _get_generator().generate_profile(
            paper_id=req.paper_id,
            metadata=req.metadata,
            abstract=req.abstract,
            full_text=req.full_text,
            in_library=req.in_library,
            agent=req.agent,
        )
        stored = _get_store().upsert_profile(profile)
        _get_index().upsert(req.paper_id, profile.get("meta", {}), chunks_generated=stored.get("chunks_upserted", 8))
        return VFGenerateResponse(
            paper_id=req.paper_id,
            chunks_upserted=int(stored.get("chunks_upserted", 0)),
            in_library=bool(profile.get("in_library", False)),
            source_type=str(profile.get("source_type", "external")),
        )
    except Exception as e:
        logger.error(f"VF generate failed for {req.paper_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def vf_batch(req: VFBatchRequest):
    results = []
    for item in req.items:
        try:
            one = await vf_generate(item)
            results.append({"paper_id": item.paper_id, "ok": True, "result": one.model_dump()})
        except Exception as e:
            results.append({"paper_id": item.paper_id, "ok": False, "error": str(e)})
    return {"total": len(req.items), "results": results}


@router.post("/sync")
async def vf_sync(req: VFSyncRequest):
    lib_path = Path(req.library_path) if req.library_path else DEFAULT_LIBRARY_PATH

    async def stream_events():
        if not lib_path.exists():
            yield f"data: {json.dumps({'status': 'error', 'message': f'library path not found: {lib_path}'})}\n\n"
            return

        files = sorted(lib_path.rglob("*.md"))
        existing = {row.get("paper_id") for row in _get_index().list(limit=200000, offset=0)}

        candidates: List[Dict[str, Any]] = []
        used_ids: Dict[str, int] = {}

        for file in files:
            content_head = _read_head(file)
            meta = _parse_md_metadata(content_head, fallback_name=file.stem)
            base_id = _build_paper_id(meta)
            used = used_ids.get(base_id, 0)
            used_ids[base_id] = used + 1
            paper_id = base_id if used == 0 else f"{base_id}_{used + 1}"
            if paper_id in existing:
                continue
            candidates.append({"paper_id": paper_id, "meta": meta, "path": str(file)})

        if req.dry_run:
            yield f"data: {json.dumps({'status': 'dry_run', 'count': len(candidates), 'new_papers': [c['paper_id'] for c in candidates]})}\n\n"
            return

        total = len(candidates)
        success = 0
        failed = 0

        for idx, item in enumerate(candidates, start=1):
            try:
                yield f"data: {json.dumps({'status': 'processing', 'processed': idx - 1, 'total': total, 'current_paper': item['paper_id']})}\n\n"
                full_text = Path(item["path"]).read_text(encoding="utf-8", errors="ignore")
                profile = await _get_generator().generate_profile(
                    paper_id=item["paper_id"],
                    metadata=item["meta"],
                    abstract=item["meta"].get("abstract", ""),
                    full_text=full_text,
                    in_library=True,
                    agent=req.agent,
                )
                stored = _get_store().upsert_profile(profile)
                _get_index().upsert(item["paper_id"], profile.get("meta", {}), chunks_generated=stored.get("chunks_upserted", 8))
                success += 1
            except Exception as e:
                failed += 1
                yield f"data: {json.dumps({'status': 'error', 'processed': idx, 'total': total, 'current_paper': item['paper_id'], 'error': str(e)})}\n\n"

        yield f"data: {json.dumps({'status': 'done', 'total': total, 'processed': total, 'success': success, 'failed': failed, 'skipped': len(files) - total})}\n\n"

    return StreamingResponse(stream_events(), media_type="text/event-stream")


@router.get("/lookup")
async def vf_lookup(
    author: Optional[str] = Query(default=None),
    year: Optional[int] = Query(default=None),
    paper_id: Optional[str] = Query(default=None),
):
    if paper_id:
        index_record = _get_index().get(paper_id)
        profile = _get_store().get_profile(paper_id)
        return {"index": index_record, "profile": profile}

    if author and year:
        return {"matches": _get_index().exact_lookup(author=author, year=year)}

    raise HTTPException(status_code=400, detail="Provide paper_id OR (author + year)")


@router.get("/stats")
async def vf_stats():
    return {
        "metadata_index": _get_index().stats(),
        "vector_store": _get_store().stats(),
    }


@router.get("/list")
async def vf_list(limit: int = 50, offset: int = 0, search: Optional[str] = None, filter: Optional[str] = None):
    items = _get_index().list(limit=max(limit, 2000), offset=offset)
    if search:
        s = search.lower().strip()
        items = [x for x in items if s in str(x.get("paper_id", "")).lower() or s in str(x.get("title", "")).lower()]
    if filter == "in_library":
        items = [x for x in items if x.get("in_library")]
    elif filter == "external":
        items = [x for x in items if not x.get("in_library")]

    return {
        "items": items[:limit],
        "limit": limit,
        "offset": offset,
    }


@router.delete("/{paper_id}")
async def vf_delete(paper_id: str):
    vec_deleted = _get_store().delete_profile(paper_id)
    idx_deleted = _get_index().delete(paper_id)
    return {
        "paper_id": paper_id,
        "vector_deleted": vec_deleted.get("deleted", 0),
        "index_deleted": idx_deleted.get("deleted", 0),
    }


def _read_head(path: Path, lines: int = 20) -> str:
    head: List[str] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            head.append(line)
            if i >= lines - 1:
                break
    return "".join(head)


def _parse_md_metadata(head: str, fallback_name: str) -> Dict[str, Any]:
    title = ""
    authors: List[str] = []
    year: Optional[int] = None

    for line in head.splitlines()[:20]:
        s = line.strip()
        if s.startswith("# ") and not title:
            title = s[2:].strip()
        if s.lower().startswith("title:") and not title:
            title = s.split(":", 1)[1].strip()
        if s.lower().startswith("authors:") or s.lower().startswith("author:"):
            val = s.split(":", 1)[1].strip()
            authors = [x.strip() for x in re.split(r"[,;]", val) if x.strip()]
        if s.lower().startswith("year:"):
            y = re.findall(r"\b(19|20)\d{2}\b", s)
            if y:
                year = int(re.search(r"\b(19|20)\d{2}\b", s).group(0))

    if not title:
        title = fallback_name.replace("_", " ").strip()
    if not year:
        m = re.search(r"\b(19|20)\d{2}\b", head + " " + fallback_name)
        if m:
            year = int(m.group(0))

    return {"title": title, "authors": authors, "year": year}


def _build_paper_id(meta: Dict[str, Any]) -> str:
    authors = meta.get("authors") if isinstance(meta.get("authors"), list) else []
    first = authors[0] if authors else "Unknown"
    last_name = re.sub(r"[^a-zA-Z0-9]", "", first.split()[-1]) or "Unknown"
    year = meta.get("year") or "0000"
    title = str(meta.get("title") or "untitled").lower()
    short_title = re.sub(r"[^a-z0-9]+", "_", title).strip("_")[:40] or "untitled"
    return f"{last_name}{year}_{short_title}"
