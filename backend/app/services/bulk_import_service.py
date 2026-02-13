"""Bulk import helpers for Explorer.

Stage 9: support listing importable files in a folder (optionally recursive)
so the frontend can import them in batch.

We keep actual conversion+artifact creation in existing endpoints.
"""

from __future__ import annotations

from pathlib import Path


IMPORTABLE_EXTS = {".docx", ".xlsx", ".xls", ".csv", ".pdf", ".txt", ".md", ".json"}


def list_importable_files(folder_path: str, *, recursive: bool = False, limit: int = 2000) -> list[str]:
    p = Path(folder_path)
    if not p.exists() or not p.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    matches: list[str] = []
    it = p.rglob("*") if recursive else p.glob("*")

    for item in it:
        if item.is_file() and item.suffix.lower() in IMPORTABLE_EXTS:
            matches.append(str(item))
            if len(matches) >= limit:
                break

    return matches
