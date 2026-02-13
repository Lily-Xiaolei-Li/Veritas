"""Health checks (no Docker dependency).

This repo enforces *no Docker* for speed and simpler testing.
Health checks focus on local machine readiness (disk/memory) and DB.

The /health endpoint is implemented in app.main; this module provides
reusable resource checks for tests and future extensions.
"""

from __future__ import annotations

import shutil

from app.config import get_settings

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    psutil = None


def check_disk_space() -> dict:
    settings = get_settings()
    stat = shutil.disk_usage(".")
    free_gb = stat.free / (1024**3)
    ok = free_gb >= settings.min_disk_space_gb
    return {
        "name": "disk_space",
        "ok": ok,
        "detail": f"{free_gb:.1f}GB available",
        "exit_code": 0 if ok else 1,
        "remediation": None
        if ok
        else f"Insufficient disk space. Need >= {settings.min_disk_space_gb}GB free.",
    }


def check_memory() -> dict:
    settings = get_settings()
    if psutil is None:  # pragma: no cover
        # best-effort: if psutil missing, don't fail health
        return {
            "name": "memory",
            "ok": True,
            "detail": "psutil not installed; memory check skipped",
            "exit_code": 0,
            "remediation": None,
        }

    mem = psutil.virtual_memory()
    avail_gb = mem.available / (1024**3)
    ok = avail_gb >= settings.min_memory_gb
    return {
        "name": "memory",
        "ok": ok,
        "detail": f"{avail_gb:.1f}GB available",
        "exit_code": 0 if ok else 1,
        "remediation": None if ok else f"Insufficient memory. Need >= {settings.min_memory_gb}GB available.",
    }


def run_resource_checks() -> dict:
    checks = [check_disk_space(), check_memory()]
    ok = all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks}
