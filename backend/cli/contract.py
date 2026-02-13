from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

SCHEMA_VERSION = "1.0"


@dataclass
class CLIError(Exception):
    code: str
    message: str
    details: Any = None
    exit_code: int = 1


class CLIBusinessError(CLIError):
    def __init__(self, code: str, message: str, details: Any = None):
        super().__init__(code=code, message=message, details=details, exit_code=1)


class CLISystemError(CLIError):
    def __init__(self, code: str, message: str, details: Any = None):
        super().__init__(code=code, message=message, details=details, exit_code=2)


def success_envelope(*, result: str = "ok", data: Any = None, meta: Any = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "result": result,
        "data": {} if data is None else data,
        "error": None,
        "meta": {} if meta is None else meta,
    }


def error_envelope(*, code: str, message: str, details: Any = None, meta: Any = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": False,
        "result": "error",
        "data": {},
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "meta": {} if meta is None else meta,
    }


def render_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)
