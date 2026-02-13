"""Legacy health checks module.

This repository enforces **NO DOCKER** for development/testing speed.

Historically Agent B included Docker daemon checks. Those have been removed.
This module remains only for backward compatibility with older imports.

Use `app.health_checks` instead.
"""

from __future__ import annotations

from app.health_checks import check_disk_space, check_memory, run_resource_checks


def run_all_checks() -> dict:
    """Backward-compatible wrapper."""
    resources = run_resource_checks()
    return {
        "ok": resources["ok"],
        "resources": resources,
    }


def as_health_payload() -> dict:
    checks = run_all_checks()
    status = "healthy" if checks["ok"] else "degraded"
    return {
        "status": status,
        "resources": checks["resources"],
    }
