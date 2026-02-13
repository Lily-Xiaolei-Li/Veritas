"""Capabilities / Dependency checks.

Stage 5: provide a simple way for the frontend to know whether optional
conversion dependencies are installed on the backend.

We intentionally keep this conservative: it checks *importability* of modules,
not that conversions will be perfect.
"""

from __future__ import annotations

import importlib.util


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def get_explorer_capabilities() -> dict:
    checks = [
        {
            "name": "docx",
            "extensions": [".docx"],
            "ok": _has_module("docx"),
            "detail": "python-docx" if _has_module("docx") else "python-docx not installed",
            "remediation": None if _has_module("docx") else "pip install python-docx",
        },
        {
            "name": "xlsx",
            "extensions": [".xlsx", ".xls", ".csv"],
            "ok": _has_module("openpyxl"),
            "detail": "openpyxl" if _has_module("openpyxl") else "openpyxl not installed",
            "remediation": None if _has_module("openpyxl") else "pip install openpyxl",
        },
        {
            "name": "pdf",
            "extensions": [".pdf"],
            "ok": _has_module("fitz"),
            "detail": "PyMuPDF" if _has_module("fitz") else "PyMuPDF not installed",
            "remediation": None if _has_module("fitz") else "pip install PyMuPDF",
        },
        {
            "name": "plain_text",
            "extensions": [".txt", ".md", ".json"],
            "ok": True,
            "detail": "built-in",
            "remediation": None,
        },
    ]

    overall_ok = all(c["ok"] for c in checks)
    return {"ok": overall_ok, "checks": checks}
