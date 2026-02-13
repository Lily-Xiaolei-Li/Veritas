from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _format_text(record: dict[str, Any]) -> str:
    return (
        f"{record['timestamp']} level={record['level']} command={record['command']} "
        f"event={record['event']} session_id={record.get('session_id')} run_id={record.get('run_id')}"
    )


def _format_jsonl(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False)


def emit_log(
    *,
    log_format: str,
    command: str,
    event: str,
    level: str = "info",
    session_id: str | None = None,
    run_id: str | None = None,
    log_file: str | None = None,
    to_stderr: bool = True,
) -> None:
    record = {
        "timestamp": _now_iso(),
        "level": level,
        "command": command,
        "event": event,
        "session_id": session_id,
        "run_id": run_id,
    }

    line = _format_jsonl(record) if log_format == "jsonl" else _format_text(record)

    if to_stderr:
        print(line, file=sys.stderr)

    if log_file:
        p = Path(log_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
