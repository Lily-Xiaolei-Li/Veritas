from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from .batch_processor import BatchProcessor
from .paper_downloader import PaperDownloader
from .paper_processor import PaperProcessor


@dataclass
class QueueTask:
    id: str
    kind: str
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    progress: dict[str, str] = field(default_factory=lambda: {
        "downloading": "pending",
        "parsing": "pending",
        "chunking": "pending",
        "embedding": "pending",
        "indexing": "pending",
    })
    input: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class KnowledgeQueue:
    def __init__(self) -> None:
        self._tasks: dict[str, QueueTask] = {}
        self._handles: dict[str, asyncio.Task] = {}
        self.downloader = PaperDownloader()
        self.processor = PaperProcessor()
        self.batch = BatchProcessor()

    async def _set_step(self, task_id: str, step: str, status: str):
        t = self._tasks.get(task_id)
        if not t:
            return
        t.progress[step] = status
        t.updated_at = datetime.now().isoformat()

    def list_tasks(self) -> list[dict[str, Any]]:
        tasks = sorted(self._tasks.values(), key=lambda x: x.created_at, reverse=True)
        return [self._serialize(t) for t in tasks]

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        t = self._tasks.get(task_id)
        return self._serialize(t) if t else None

    def stats(self) -> dict[str, Any]:
        total = len(self._tasks)
        completed = sum(1 for t in self._tasks.values() if t.status == "completed")
        failed = sum(1 for t in self._tasks.values() if t.status == "failed")
        running = sum(1 for t in self._tasks.values() if t.status == "running")
        return {"total": total, "completed": completed, "failed": failed, "running": running}

    def cancel(self, task_id: str) -> bool:
        h = self._handles.get(task_id)
        if h and not h.done():
            h.cancel()
            t = self._tasks.get(task_id)
            if t:
                t.status = "cancelled"
                t.updated_at = datetime.now().isoformat()
            return True
        return False

    def enqueue_download(self, payload: dict[str, Any]) -> str:
        task_id = str(uuid4())
        task = QueueTask(id=task_id, kind="download", input=payload)
        self._tasks[task_id] = task
        self._handles[task_id] = asyncio.create_task(self._run_download(task_id, payload))
        return task_id

    def enqueue_upload(self, files: list[str]) -> str:
        task_id = str(uuid4())
        task = QueueTask(id=task_id, kind="upload", input={"files": files})
        self._tasks[task_id] = task
        self._handles[task_id] = asyncio.create_task(self._run_upload(task_id, files))
        return task_id

    def enqueue_batch(self, payload: dict[str, Any]) -> str:
        task_id = str(uuid4())
        task = QueueTask(id=task_id, kind="batch", input=payload)
        self._tasks[task_id] = task
        self._handles[task_id] = asyncio.create_task(self._run_batch(task_id, payload))
        return task_id

    async def _run_download(self, task_id: str, payload: dict[str, Any]):
        t = self._tasks[task_id]
        t.status = "running"
        await self._set_step(task_id, "downloading", "running")
        try:
            dl = await self.downloader.download(doi=payload.get("doi"), title=payload.get("title"), url=payload.get("url"))
            if dl.get("status") != "success":
                await self._set_step(task_id, "downloading", "failed")
                t.status = "failed"
                t.result = dl
                t.error = dl.get("error")
                return
            await self._set_step(task_id, "downloading", "done")

            processed = await self.processor.process(dl["file_path"], task_id, self._set_step)
            if processed.get("status") != "success":
                t.status = "failed"
                t.error = processed.get("error")
                t.result = {"download": dl, "processing": processed}
                return

            t.status = "completed"
            t.result = {"download": dl, "processing": processed}
        except asyncio.CancelledError:
            t.status = "cancelled"
        except Exception as e:
            t.status = "failed"
            t.error = str(e)
        finally:
            t.updated_at = datetime.now().isoformat()

    async def _run_upload(self, task_id: str, files: list[str]):
        t = self._tasks[task_id]
        t.status = "running"
        results = []
        for fp in files:
            await self._set_step(task_id, "parsing", "running")
            r = await self.processor.process(fp, task_id, self._set_step)
            results.append({"file": fp, **r})
        t.status = "completed" if all(x.get("status") == "success" for x in results) else "failed"
        t.result = {"items": results}
        t.updated_at = datetime.now().isoformat()

    async def _run_batch(self, task_id: str, payload: dict[str, Any]):
        t = self._tasks[task_id]
        t.status = "running"

        entries: list[dict[str, Any]] = []
        if payload.get("csv_data"):
            entries.extend(self.batch.parse_csv(payload["csv_data"]))
        if payload.get("dois"):
            entries.extend({"doi": d} for d in self.batch.parse_dois(payload["dois"]))
        if payload.get("bibtex"):
            entries.extend(self.batch.parse_bibtex(payload["bibtex"]))

        results = []
        for e in entries:
            if t.status == "cancelled":
                break
            dl = await self.downloader.download(doi=e.get("doi"), title=e.get("title"))
            if dl.get("status") == "success":
                proc = await self.processor.process(dl["file_path"], task_id, self._set_step)
            else:
                proc = {"status": "skipped"}
            results.append({"input": e, "download": dl, "processing": proc})
            t.result = {
                "total": len(entries),
                "completed": len(results),
                "items": results,
            }
            t.updated_at = datetime.now().isoformat()

        ok = [x for x in results if x.get("processing", {}).get("status") == "success"]
        t.status = "completed" if len(ok) == len(results) else "failed"

    def _serialize(self, t: QueueTask | None) -> dict[str, Any]:
        if not t:
            return {}
        return {
            "id": t.id,
            "kind": t.kind,
            "status": t.status,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
            "progress": t.progress,
            "input": t.input,
            "result": t.result,
            "error": t.error,
        }


knowledge_queue = KnowledgeQueue()
