from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.knowledge_source import PaperFinder, knowledge_queue

router = APIRouter(prefix="/knowledge-source", tags=["knowledge-source"])
finder = PaperFinder()


class DownloadRequest(BaseModel):
    doi: str | None = None
    title: str | None = None
    url: str | None = None


class BatchRequest(BaseModel):
    csv_data: str | None = None
    dois: str | None = None
    bibtex: str | None = None


@router.get("/search")
async def search_papers(q: str):
    if not q.strip():
        raise HTTPException(status_code=400, detail="q is required")
    return {"items": finder.search(q)}


@router.post("/download")
async def download_paper(req: DownloadRequest):
    if not any([req.doi, req.title, req.url]):
        raise HTTPException(status_code=400, detail="one of doi/title/url is required")
    task_id = knowledge_queue.enqueue_download(req.model_dump())
    return {"task_id": task_id, "status": "queued"}


@router.post("/batch")
async def batch_import(req: BatchRequest):
    if not any([req.csv_data, req.dois, req.bibtex]):
        raise HTTPException(status_code=400, detail="csv_data/dois/bibtex is required")
    task_id = knowledge_queue.enqueue_batch(req.model_dump())
    return {"task_id": task_id, "status": "queued"}


@router.post("/upload")
async def upload_pdfs(files: list[UploadFile] = File(...)):
    save_dir = Path("data/uploads/knowledge")
    save_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in files:
        if not f.filename:
            continue
        out = save_dir / f.filename
        out.write_bytes(await f.read())
        paths.append(str(out.resolve()))

    if not paths:
        raise HTTPException(status_code=400, detail="no files uploaded")

    task_id = knowledge_queue.enqueue_upload(paths)
    return {"task_id": task_id, "count": len(paths), "status": "queued"}


@router.get("/queue")
async def queue_list():
    return {"items": knowledge_queue.list_tasks()}


@router.get("/queue/{task_id}")
async def queue_get(task_id: str):
    item = knowledge_queue.get_task(task_id)
    if not item:
        raise HTTPException(status_code=404, detail="task not found")
    return item


@router.delete("/queue/{task_id}")
async def queue_cancel(task_id: str):
    ok = knowledge_queue.cancel(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="task not found or not cancellable")
    return {"ok": True}


@router.get("/stats")
async def queue_stats():
    return knowledge_queue.stats()
