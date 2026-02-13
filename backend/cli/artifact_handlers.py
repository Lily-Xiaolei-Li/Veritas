from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from .contract import CLIBusinessError, success_envelope
from .state_store import create_artifact_api, load_state, now_iso, save_state


def _session_exists(state: dict, session_id: str) -> bool:
    return any(s.get("id") == session_id for s in state.get("sessions", []))


def _run_exists(state: dict, run_id: str) -> bool:
    return any(r.get("id") == run_id for r in state.get("runs", []))


def _read_content_from_args(args) -> tuple[str, str | None]:
    selected = [bool(args.content), bool(args.file)]
    if sum(selected) != 1:
        raise CLIBusinessError(
            code="ARTIFACT_INPUT_REQUIRED",
            message="Exactly one of --content/--file is required",
        )

    if args.content:
        return args.content, None

    p = Path(args.file)
    if not p.exists() or not p.is_file():
        raise CLIBusinessError(code="ARTIFACT_FILE_NOT_FOUND", message="Artifact file not found", details={"file": args.file})

    return p.read_text(encoding="utf-8"), str(p.resolve())


def artifact_create(args):
    if not args.session:
        raise CLIBusinessError(code="ARTIFACT_SESSION_REQUIRED", message="--session is required")

    state = load_state()
    if not _session_exists(state, args.session):
        raise CLIBusinessError(code="SESSION_NOT_FOUND", message="Session not found", details={"session": args.session})

    provenance_type = args.provenance_type or "manual"
    if provenance_type not in {"run", "imported", "manual"}:
        raise CLIBusinessError(code="ARTIFACT_PROVENANCE_INVALID", message="Invalid provenance type")

    run_id = args.run
    if provenance_type == "run":
        if not run_id:
            raise CLIBusinessError(code="ARTIFACT_RUN_REQUIRED", message="--run is required when provenance type is run")
        if not _run_exists(state, run_id):
            raise CLIBusinessError(code="RUN_NOT_FOUND", message="Run not found", details={"run": run_id})
    else:
        # imported/manual allow run_id to be omitted.
        if run_id and not _run_exists(state, run_id):
            raise CLIBusinessError(code="RUN_NOT_FOUND", message="Run not found", details={"run": run_id})

    content, file_ref = _read_content_from_args(args)
    ts = now_iso()
    art_id = f"art_{uuid4().hex[:10]}"

    artifact = {
        "id": art_id,
        "session_id": args.session,
        "run_id": run_id,
        "name": args.name or f"artifact-{art_id}.md",
        "type": args.type,
        "content": content,
        "created_at": ts,
        "updated_at": ts,
        "provenance": {
            "type": provenance_type,
            "file": file_ref,
        },
    }

    # Sync to API (for GUI)
    api_result = create_artifact_api(args.session, run_id, artifact["name"], content, args.type)
    if api_result:
        artifact["id"] = api_result.get("id", artifact["id"])

    state.setdefault("artifacts", []).append(artifact)
    save_state(state)

    return success_envelope(result="created", data={"artifact": artifact})


def artifact_list(args):
    state = load_state()
    if not args.session:
        raise CLIBusinessError(code="ARTIFACT_SESSION_REQUIRED", message="--session is required")
    if not _session_exists(state, args.session):
        raise CLIBusinessError(code="SESSION_NOT_FOUND", message="Session not found", details={"session": args.session})

    artifacts = [a for a in state.get("artifacts", []) if a.get("session_id") == args.session]
    artifacts = sorted(artifacts, key=lambda a: (a.get("created_at", ""), a.get("id", "")))
    return success_envelope(result="ok", data={"session_id": args.session, "artifacts": artifacts})


def artifact_show(args):
    if not args.artifact:
        raise CLIBusinessError(code="ARTIFACT_ID_REQUIRED", message="--artifact is required")

    state = load_state()
    art = next((a for a in state.get("artifacts", []) if a.get("id") == args.artifact), None)
    if not art:
        raise CLIBusinessError(code="ARTIFACT_NOT_FOUND", message="Artifact not found", details={"artifact": args.artifact})
    return success_envelope(result="ok", data={"artifact": art})


def artifact_export(args):
    if not args.artifact:
        raise CLIBusinessError(code="ARTIFACT_ID_REQUIRED", message="--artifact is required")
    if not args.out:
        raise CLIBusinessError(code="ARTIFACT_OUT_REQUIRED", message="--out is required")

    state = load_state()
    art = next((a for a in state.get("artifacts", []) if a.get("id") == args.artifact), None)
    if not art:
        raise CLIBusinessError(code="ARTIFACT_NOT_FOUND", message="Artifact not found", details={"artifact": args.artifact})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(art.get("content", ""), encoding="utf-8")

    return success_envelope(
        result="ok",
        data={
            "artifact_id": art["id"],
            "out": str(out),
            "bytes": out.stat().st_size,
        },
    )


def artifact_delete(args):
    if not args.artifact:
        raise CLIBusinessError(code="ARTIFACT_ID_REQUIRED", message="--artifact is required")
    if not getattr(args, "yes", False):
        raise CLIBusinessError(code="ARTIFACT_DELETE_CONFIRM_REQUIRED", message="Use --yes to confirm artifact deletion")

    state = load_state()
    artifacts = state.get("artifacts", [])
    idx = next((i for i, a in enumerate(artifacts) if a.get("id") == args.artifact), None)
    if idx is None:
        raise CLIBusinessError(code="ARTIFACT_NOT_FOUND", message="Artifact not found", details={"artifact": args.artifact})

    removed = artifacts.pop(idx)

    save_state(state)
    return success_envelope(result="deleted", data={"artifact": removed})
