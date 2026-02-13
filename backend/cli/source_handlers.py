from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from .contract import CLIBusinessError, success_envelope
from .state_store import load_state, now_iso, save_state


def _session_exists(state: dict, session_id: str) -> bool:
    return any(s.get("id") == session_id for s in state.get("sessions", []))


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise CLIBusinessError(code="SOURCE_URL_INVALID", message="Invalid URL", details={"url": url})
    normalized = f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path or ''}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def source_add(args):
    state = load_state()
    if not args.session:
        raise CLIBusinessError(code="SOURCE_SESSION_REQUIRED", message="--session is required")
    if not _session_exists(state, args.session):
        raise CLIBusinessError(code="SESSION_NOT_FOUND", message="Session not found", details={"session": args.session})

    selected = [bool(args.file), bool(args.url), bool(args.text)]
    if sum(selected) != 1:
        raise CLIBusinessError(
            code="SOURCE_INPUT_REQUIRED",
            message="Exactly one of --file/--url/--text is required",
        )

    kind: str
    locator: str
    content_hash: str

    if args.file:
        p = Path(args.file)
        if not p.exists() or not p.is_file():
            raise CLIBusinessError(code="SOURCE_FILE_NOT_FOUND", message="Source file not found", details={"file": args.file})
        kind = "file"
        locator = str(p.resolve())
        content_hash = _hash_file(p)
    elif args.url:
        kind = "url"
        locator = _normalize_url(args.url)
        content_hash = _hash_text(locator)
    else:
        kind = "text"
        locator = args.text
        content_hash = _hash_text(locator)

    sources = state.setdefault("sources", [])
    idem = state.setdefault("idempotency", {})

    idem_key = args.idempotency_key
    if idem_key and idem_key in idem:
        src_id = idem[idem_key]
        found = next((s for s in sources if s.get("id") == src_id), None)
        if found:
            return success_envelope(result="nochange", data={"source": found}, meta={"idempotency_key": idem_key})

    # In automation mode dedupe defaults to enabled unless caller disables by omission in interactive mode.
    dedupe = bool(args.dedupe or getattr(args, "automation", False))
    if dedupe:
        found = next(
            (
                s
                for s in sources
                if s.get("session_id") == args.session and s.get("content_hash") == content_hash and s.get("kind") == kind
            ),
            None,
        )
        if found:
            return success_envelope(result="nochange", data={"source": found}, meta={"dedupe": True})

    ts = now_iso()
    src = {
        "id": f"src_{uuid4().hex[:10]}",
        "session_id": args.session,
        "kind": kind,
        "locator": locator,
        "content_hash": content_hash,
        "tags": [],
        "created_at": ts,
        "updated_at": ts,
    }
    sources.append(src)

    if idem_key:
        idem[idem_key] = src["id"]

    save_state(state)
    return success_envelope(result="created", data={"source": src}, meta={"idempotency_key": idem_key, "dedupe": dedupe})


def source_list(args):
    state = load_state()
    session_id = args.session
    sources = state.get("sources", [])
    if session_id:
        if not _session_exists(state, session_id):
            raise CLIBusinessError(code="SESSION_NOT_FOUND", message="Session not found", details={"session": session_id})
        sources = [s for s in sources if s.get("session_id") == session_id]

    sources = sorted(sources, key=lambda s: (s.get("created_at", ""), s.get("id", "")))
    return success_envelope(result="ok", data={"sources": sources, "session_id": session_id})


def source_show(args):
    if not args.source:
        raise CLIBusinessError(code="SOURCE_ID_REQUIRED", message="--source is required")

    state = load_state()
    src = next((s for s in state.get("sources", []) if s.get("id") == args.source), None)
    if not src:
        raise CLIBusinessError(code="SOURCE_NOT_FOUND", message="Source not found", details={"source": args.source})
    return success_envelope(result="ok", data={"source": src})


def source_remove(args):
    if not args.source:
        raise CLIBusinessError(code="SOURCE_ID_REQUIRED", message="--source is required")
    if not getattr(args, "yes", False):
        raise CLIBusinessError(code="SOURCE_DELETE_CONFIRM_REQUIRED", message="Use --yes to confirm source removal")

    state = load_state()
    sources = state.get("sources", [])
    idx = next((i for i, s in enumerate(sources) if s.get("id") == args.source), None)
    if idx is None:
        raise CLIBusinessError(code="SOURCE_NOT_FOUND", message="Source not found", details={"source": args.source})

    removed = sources.pop(idx)
    save_state(state)
    return success_envelope(result="deleted", data={"source": removed})


def source_tag(args):
    if not args.source:
        raise CLIBusinessError(code="SOURCE_ID_REQUIRED", message="--source is required")
    if not args.tag:
        raise CLIBusinessError(code="SOURCE_TAG_REQUIRED", message="--tag is required")

    state = load_state()
    src = next((s for s in state.get("sources", []) if s.get("id") == args.source), None)
    if not src:
        raise CLIBusinessError(code="SOURCE_NOT_FOUND", message="Source not found", details={"source": args.source})

    tags = src.setdefault("tags", [])
    if args.tag in tags:
        return success_envelope(result="nochange", data={"source": src})

    tags.append(args.tag)
    src["updated_at"] = now_iso()
    save_state(state)
    return success_envelope(result="updated", data={"source": src})
