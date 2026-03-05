from __future__ import annotations

import json

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.utils.config import Settings
from app.utils.excel_probe import inspect_excel
from app.utils.qdrant_client import get_profile, search_profiles, validate_collection
from app.utils.slr_viz import load_heatmap_sheets, load_profile_filter_options, load_timeline_data
from app.utils.scholar_influence import run_scholar_analysis

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


class ChatRequest(BaseModel):
    message: str
    context: str | None = None
    button_prompt: str | None = None


def _collect_sse_text(response: requests.Response) -> tuple[str, list[dict[str, str]]]:
    text_parts: list[str] = []
    artifacts: list[dict[str, str]] = []
    for raw in response.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        payload = raw.removeprefix("data:").strip()
        if not payload or payload == "[DONE]":
            continue

        try:
            event_data = json.loads(payload)
        except Exception:
            continue

        if not isinstance(event_data, dict):
            continue

        event_type = str(event_data.get("type", "")).lower()
        if event_type == "token" and event_data.get("content") is not None:
            text_parts.append(str(event_data["content"]))
        elif event_type == "artifact":
            artifacts.append(
                {
                    "filename": str(event_data.get("filename", "artifact.md")),
                    "content": str(event_data.get("content", "")),
                }
            )
    return " ".join(text_parts).strip(), artifacts


@router.get("/health")
def health() -> dict:
    """Service health endpoint used by docker healthcheck and smoke tests."""
    return {"status": "ok", "service": "gp-viz-api"}


@router.get("/version")
def version() -> dict:
    return {"version": "0.1.0"}


@router.get("/check")
def check() -> dict:
    settings = Settings.from_env()
    ok = validate_collection(settings.qdrant_base_url, settings.data_source_collection)
    return {
        "qdrant_ok": ok,
        "collection": settings.data_source_collection,
        "base_url": settings.qdrant_base_url,
        "excel_path": settings.excel_path,
        "pdf_dir": settings.pdf_dir,
    }


@router.get("/papers")
def search_papers(query: str, limit: int = 10):
    if not query.strip():
        raise HTTPException(status_code=400, detail="query is required")

    settings = Settings.from_env()
    result = search_profiles(
        settings.qdrant_base_url,
        settings.data_source_collection,
        query=query,
        limit=limit,
    )
    return {
        "query": query,
        "count": len(result.records),
        "collection": result.collection,
        "results": [record.as_dict() for record in result.records],
    }


@router.get("/papers/{paper_id}")
def get_paper(paper_id: str):
    settings = Settings.from_env()
    record = get_profile(settings.qdrant_base_url, settings.data_source_collection, paper_id)
    if not record:
        raise HTTPException(status_code=404, detail="Paper not found")
    return record.as_dict()


@router.get("/meta")
def metadata() -> dict:
    settings = Settings.from_env()
    payload = {"excel": None, "qdrant_collection_exists": validate_collection(
        settings.qdrant_base_url,
        settings.data_source_collection,
    )}
    try:
        payload["excel"] = inspect_excel(settings.excel_path).asdict()
    except Exception as exc:
        payload["excel_error"] = str(exc)
    return payload


@router.get("/viz/f1")
def viz_timeline() -> dict:
    """F1: stacked area timeline data from Excel sheet."""
    settings = Settings.from_env()
    try:
        return load_timeline_data(settings)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/viz/f2")
def viz_heatmaps() -> dict:
    """F2: theme heatmaps data from one or more Excel sheets."""
    settings = Settings.from_env()
    try:
        sheets = load_heatmap_sheets(settings)
        return {"sheets": sheets, "count": len(sheets)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/viz/filters")
def viz_filters() -> dict:
    settings = Settings.from_env()
    return load_profile_filter_options(settings)


@router.post("/assist")
def assist(payload: SearchRequest):
    settings = Settings.from_env()
    result = search_profiles(
        settings.qdrant_base_url,
        settings.data_source_collection,
        payload.query,
        limit=payload.limit,
    )
    return {
        "query": payload.query,
        "count": len(result.records),
        "results": [record.as_dict() for record in result.records],
    }


@router.post("/assist-stream")
def assist_stream(payload: ChatRequest):
    """Proxy XiaoLei `/chat` SSE into structured JSON text+artifact output."""
    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    settings = Settings.from_env()
    try:
        resp = requests.post(
            f"{settings.xiaolei_url.rstrip('/')}/chat",
            json=payload.dict(),
            timeout=20,
            stream=True,
        )
        resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"xiaolei_api unavailable: {exc}") from exc

    merged, artifacts = _collect_sse_text(resp)
    return {
        "message": payload.message,
        "assistant_text": merged,
        "artifacts": artifacts,
    }


@router.get("/scholar-influence/{scholar_name}")
def scholar_influence(scholar_name: str, collection: str = "vf_profiles_slr") -> dict:
    """Analyze influence of a specific scholar (e.g., Power) in the corpus.
    
    Returns citation counts, categories (theoretical/framework/method/etc.), 
    time trends, and per-paper breakdown.
    """
    settings = Settings.from_env()
    try:
        result = run_scholar_analysis(
            scholar=scholar_name,
            qdrant_host=settings.qdrant_host,
            qdrant_port=settings.qdrant_port,
            collection=collection,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
