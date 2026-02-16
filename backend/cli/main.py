from __future__ import annotations

import argparse
import sys
from typing import Callable, Optional

from .artifact_handlers import (
    artifact_copy,
    artifact_create,
    artifact_delete,
    artifact_draft_save,
    artifact_draft_show,
    artifact_export,
    artifact_list,
    artifact_preview,
    artifact_rename,
    artifact_show,
    artifact_update,
)
from .chat_handlers import chat_history, chat_send
from .checker_handlers import checker_results, checker_run, checker_status
from .citalio_handlers import citalio_results, citalio_run, citalio_status
from .proliferomaxima_handlers import proliferomaxima_results, proliferomaxima_run, proliferomaxima_status
from .vf_middleware_handlers import vf_batch, vf_delete, vf_generate, vf_list, vf_lookup, vf_stats, vf_sync
from .context_handlers import context_clear, context_get, context_resolve, context_set
from .contract import (
    CLIBusinessError,
    CLIError,
    CLISystemError,
    error_envelope,
    render_json,
    success_envelope,
)
from .log_handlers import log_recent, log_stream
from .logger import emit_log
from .mode import detect_mode
from .persona_handlers import (
    persona_create,
    persona_export,
    persona_import,
    persona_list,
    persona_select,
    persona_show,
    persona_update,
    persona_version,
)
from .run_handlers import run_cancel, run_list, run_resume, run_retry, run_show
from .session_handlers import (
    session_create,
    session_current,
    session_list,
    session_show,
    session_use,
)
from .source_handlers import (
    source_add,
    source_batch,
    source_download,
    source_list,
    source_queue,
    source_remove,
    source_search,
    source_show,
    source_stats,
    source_tag,
    source_upload,
    source_proxy_download,
)
from .status_handlers import status_doctor, status_show

Handler = Callable[[argparse.Namespace], dict]


class CLIArgumentParser(argparse.ArgumentParser):
    def error(self, message: str):
        raise CLIBusinessError(code="CLI_INVALID_ARGUMENTS", message="Invalid command arguments", details=message)


def _print(args: argparse.Namespace, payload: dict) -> None:
    if getattr(args, "json", False):
        print(render_json(payload))
    elif not getattr(args, "quiet", False):
        if payload.get("ok"):
            print(f"[OK] {payload.get('result', 'ok')}")
        else:
            err = payload.get("error") or {}
            print(f"[ERROR] {err.get('code', 'UNKNOWN')}: {err.get('message', '')}", file=sys.stderr)


def noop_handler(args: argparse.Namespace) -> dict:
    mode = detect_mode(
        force_automation=bool(getattr(args, "automation", False)),
        force_interactive=bool(getattr(args, "interactive", False)),
        stdin_isatty=sys.stdin.isatty(),
    )

    if getattr(args, "simulate_system_error", False):
        raise CLISystemError(
            code="CLI_SIMULATED_SYSTEM_ERROR",
            message="Simulated runtime/system failure",
            details="Used for contract and exit-code verification",
        )

    return success_envelope(
        result="ok",
        data={
            "resource": getattr(args, "resource", "unknown"),
            "action": getattr(args, "action", "unknown"),
        },
        meta={"mode": mode.value, "mode_source": mode.source},
    )


def _add_global_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--api-version", default="1", help="CLI/API contract version (default: 1)")
    parser.add_argument(
        "--log-format",
        choices=["text", "jsonl"],
        default="text",
        help="Log output format",
    )
    parser.add_argument("--log-file", default=None, help="Optional log file path")
    parser.add_argument("--quiet", action="store_true", help="Suppress non-essential terminal output")
    parser.add_argument("--yes", action="store_true", help="Auto-confirm destructive operations")
    parser.add_argument(
        "--use-current-session",
        action="store_true",
        help="Use saved current session when --session is omitted",
    )
    parser.add_argument(
        "--automation",
        action="store_true",
        help="Force automation mode (overrides TTY detection)",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Force interactive mode (overrides TTY detection)",
    )
    parser.add_argument(
        "--simulate-system-error",
        action="store_true",
        help=argparse.SUPPRESS,
    )


def _resource_actions() -> dict[str, list[str]]:
    return {
        "session": ["create", "list", "show", "update", "archive", "restore", "delete", "use", "current"],
        "context": ["set", "get", "clear", "resolve"],
        "source": ["add", "list", "show", "remove", "tag", "search", "download", "upload", "batch", "queue", "stats", "proxy-download"],
        "persona": ["create", "list", "show", "update", "version", "select", "export", "import"],
        "chat": ["send", "history", "retry"],
        "artifact": ["create", "list", "show", "export", "delete", "rename", "copy", "update", "preview", "draft"],
        "run": ["list", "show", "retry", "resume", "cancel"],
        "config": ["get", "set", "list"],
        "status": ["show", "doctor"],
        "checker": ["run", "status", "results"],
        "citalio": ["run", "status", "results"],
        "proliferomaxima": ["run", "status", "results"],
        "vf": ["generate", "batch", "lookup", "stats", "list", "delete", "sync"],
        "log": ["stream", "recent"],
    }


def _artifact_draft_dispatch(args):
    if getattr(args, "save", False):
        return artifact_draft_save(args)
    return artifact_draft_show(args)


def _handler_for(resource: str, action: str) -> Handler:
    if resource == "session" and action == "create":
        return session_create
    if resource == "session" and action == "show":
        return session_show
    if resource == "session" and action == "list":
        return session_list
    if resource == "session" and action == "use":
        return session_use
    if resource == "session" and action == "current":
        return session_current

    if resource == "context" and action == "set":
        return context_set
    if resource == "context" and action == "get":
        return context_get
    if resource == "context" and action == "clear":
        return context_clear
    if resource == "context" and action == "resolve":
        return context_resolve

    if resource == "chat" and action == "send":
        return chat_send
    if resource == "chat" and action == "history":
        return chat_history

    if resource == "source" and action == "add":
        return source_add
    if resource == "source" and action == "list":
        return source_list
    if resource == "source" and action == "show":
        return source_show
    if resource == "source" and action == "remove":
        return source_remove
    if resource == "source" and action == "tag":
        return source_tag
    if resource == "source" and action == "search":
        return source_search
    if resource == "source" and action == "download":
        return source_download
    if resource == "source" and action == "upload":
        return source_upload
    if resource == "source" and action == "batch":
        return source_batch
    if resource == "source" and action == "queue":
        return source_queue
    if resource == "source" and action == "stats":
        return source_stats
    if resource == "source" and action == "proxy-download":
        return source_proxy_download

    if resource == "persona" and action == "create":
        return persona_create
    if resource == "persona" and action == "list":
        return persona_list
    if resource == "persona" and action == "show":
        return persona_show
    if resource == "persona" and action == "update":
        return persona_update
    if resource == "persona" and action == "version":
        return persona_version
    if resource == "persona" and action == "select":
        return persona_select
    if resource == "persona" and action == "export":
        return persona_export
    if resource == "persona" and action == "import":
        return persona_import

    if resource == "artifact" and action == "create":
        return artifact_create
    if resource == "artifact" and action == "list":
        return artifact_list
    if resource == "artifact" and action == "show":
        return artifact_show
    if resource == "artifact" and action == "export":
        return artifact_export
    if resource == "artifact" and action == "delete":
        return artifact_delete
    if resource == "artifact" and action == "rename":
        return artifact_rename
    if resource == "artifact" and action == "copy":
        return artifact_copy
    if resource == "artifact" and action == "update":
        return artifact_update
    if resource == "artifact" and action == "preview":
        return artifact_preview
    if resource == "artifact" and action == "draft":
        return _artifact_draft_dispatch

    if resource == "run" and action == "list":
        return run_list
    if resource == "run" and action == "show":
        return run_show
    if resource == "run" and action == "retry":
        return run_retry
    if resource == "run" and action == "resume":
        return run_resume
    if resource == "run" and action == "cancel":
        return run_cancel

    if resource == "status" and action == "show":
        return status_show
    if resource == "status" and action == "doctor":
        return status_doctor

    if resource == "checker" and action == "run":
        return checker_run
    if resource == "checker" and action == "status":
        return checker_status
    if resource == "checker" and action == "results":
        return checker_results

    if resource == "citalio" and action == "run":
        return citalio_run
    if resource == "citalio" and action == "status":
        return citalio_status
    if resource == "citalio" and action == "results":
        return citalio_results

    if resource == "proliferomaxima" and action == "run":
        return proliferomaxima_run
    if resource == "proliferomaxima" and action == "status":
        return proliferomaxima_status
    if resource == "proliferomaxima" and action == "results":
        return proliferomaxima_results

    if resource == "vf" and action == "generate":
        return vf_generate
    if resource == "vf" and action == "batch":
        return vf_batch
    if resource == "vf" and action == "lookup":
        return vf_lookup
    if resource == "vf" and action == "stats":
        return vf_stats
    if resource == "vf" and action == "list":
        return vf_list
    if resource == "vf" and action == "delete":
        return vf_delete
    if resource == "vf" and action == "sync":
        return vf_sync

    if resource == "log" and action == "stream":
        return log_stream
    if resource == "log" and action == "recent":
        return log_recent

    return noop_handler


def _configure_action_parser(resource: str, action: str, action_parser: argparse.ArgumentParser) -> None:
    if resource == "session" and action == "create":
        action_parser.add_argument("--name", required=True, help="Session name")
        action_parser.add_argument("--idempotency-key", default=None, help="Idempotency key")
        action_parser.add_argument(
            "--dedupe-name",
            action="store_true",
            help="Alias for name-based idempotency behavior",
        )
    elif resource == "session" and action == "show":
        action_parser.add_argument("--session", required=True, help="Session ID")
    elif resource == "session" and action == "use":
        action_parser.add_argument("--session", required=True, help="Session ID")

    elif resource == "context" and action in {"set", "get", "clear"}:
        action_parser.add_argument("--scope", choices=["global", "session", "run"], required=True)
        action_parser.add_argument("--session", default=None, help="Session ID (required for session scope)")
        action_parser.add_argument("--run", default=None, help="Run ID (required for run scope)")
        if action == "set":
            action_parser.add_argument("--content", required=True, help="Context content")

    elif resource == "context" and action == "resolve":
        action_parser.add_argument("--session", default=None, help="Optional session ID")
        action_parser.add_argument("--run", default=None, help="Optional run ID")

    elif resource == "chat" and action == "send":
        action_parser.add_argument("--session", default=None, help="Session ID")
        action_parser.add_argument("--message", default=None, help="Message content")
        action_parser.add_argument("--persona", default=None, help="Persona ID (e.g. templator, drafter)")
        action_parser.add_argument("--artifacts", default=None, help="Comma-separated artifact IDs to include as context")
        action_parser.add_argument("--rag", default=None, help="Comma-separated RAG sources to search (e.g. library,interviews)")
        action_parser.add_argument("--rag-top-k", type=int, default=5, help="Number of RAG results per source (default: 5)")
        action_parser.add_argument("--stream", action="store_true", help="Stream token output")

    elif resource == "chat" and action == "history":
        action_parser.add_argument("--session", default=None, help="Session ID")

    elif resource == "source" and action == "add":
        action_parser.add_argument("--session", default=None, help="Session ID")
        action_parser.add_argument("--idempotency-key", default=None, help="Idempotency key")
        action_parser.add_argument("--dedupe", action="store_true", help="Dedupe within session by content hash")
        action_parser.add_argument("--file", default=None, help="Source file path")
        action_parser.add_argument("--url", default=None, help="Source URL")
        action_parser.add_argument("--text", default=None, help="Inline source text")
    elif resource == "source" and action == "list":
        action_parser.add_argument("--session", default=None, help="Optional session ID")
    elif resource == "source" and action in {"show", "remove", "tag"}:
        action_parser.add_argument("--source", default=None, help="Source ID")
        if action == "tag":
            action_parser.add_argument("--tag", default=None, help="Tag text")
    elif resource == "source" and action == "search":
        action_parser.add_argument("query", nargs="?", default=None, help="Search query")
    elif resource == "source" and action == "download":
        action_parser.add_argument("--doi", default=None)
        action_parser.add_argument("--title", default=None)
        action_parser.add_argument("--url", default=None)
    elif resource == "source" and action == "upload":
        action_parser.add_argument("path", nargs="?", default=None, help="PDF file or folder path")
    elif resource == "source" and action == "batch":
        action_parser.add_argument("--csv", default=None, help="CSV file path")
        action_parser.add_argument("--dois", default=None, help="DOI list file path")
        action_parser.add_argument("--bibtex", default=None, help="BibTeX file path")
    elif resource == "source" and action == "proxy-download":
        action_parser.add_argument("--doi", action="append", default=None, help="Single DOI (repeatable)")
        action_parser.add_argument("--doi-list", default=None, help="Text file containing DOI list")
        action_parser.add_argument("--out", default=None, help="Output queue JSON path (default: data/downloads/knowledge/proxy_queue.json)")

    elif resource == "persona" and action == "create":
        action_parser.add_argument("--name", required=True, help="Persona name")
        action_parser.add_argument("--system-prompt", required=True, help="System prompt")
    elif resource == "persona" and action in {"show", "update", "version", "export", "select"}:
        action_parser.add_argument("--persona", default=None, help="Persona ID")
        if action == "update":
            action_parser.add_argument("--name", default=None, help="Persona name")
            action_parser.add_argument("--system-prompt", default=None, help="System prompt")
        if action == "version":
            action_parser.add_argument("--bump", action="store_true", help="Bump persona version")
        if action == "export":
            action_parser.add_argument("--out", default=None, help="Output file path")
        if action == "select":
            action_parser.add_argument("--session", default=None, help="Session ID")
    elif resource == "persona" and action == "import":
        action_parser.add_argument("--file", default=None, help="Persona file path")

    elif resource == "artifact" and action == "create":
        action_parser.add_argument("--session", default=None, help="Session ID")
        action_parser.add_argument("--name", default=None, help="Artifact name")
        action_parser.add_argument("--type", default="markdown", help="Artifact type")
        action_parser.add_argument("--content", default=None, help="Inline content")
        action_parser.add_argument("--file", default=None, help="File path as content source")
        action_parser.add_argument("--provenance-type", default="manual", choices=["run", "imported", "manual"])
        action_parser.add_argument("--run", default=None, help="Run ID (required for provenance type run)")
    elif resource == "artifact" and action == "list":
        action_parser.add_argument("--session", default=None, help="Session ID")
    elif resource == "artifact" and action in {"show", "export", "delete"}:
        action_parser.add_argument("--artifact", default=None, help="Artifact ID")
        if action == "export":
            action_parser.add_argument("--out", default=None, help="Output file path")
    elif resource == "artifact" and action == "rename":
        action_parser.add_argument("--artifact", required=True, help="Artifact ID")
        action_parser.add_argument("--name", required=True, help="New name for the artifact")
    elif resource == "artifact" and action == "copy":
        action_parser.add_argument("--artifact", required=True, help="Artifact ID to copy")
    elif resource == "artifact" and action == "update":
        action_parser.add_argument("--artifact", required=True, help="Artifact ID")
        action_parser.add_argument("--content", default=None, help="New content (inline)")
        action_parser.add_argument("--file", default=None, help="File path with new content")
    elif resource == "artifact" and action == "preview":
        action_parser.add_argument("--artifact", required=True, help="Artifact ID")
    elif resource == "artifact" and action == "draft":
        # Draft is a sub-resource with show/save sub-actions
        action_parser.add_argument("--artifact", required=True, help="Artifact ID")
        action_parser.add_argument("--save", action="store_true", help="Save draft (default: show draft)")
        action_parser.add_argument("--content", default=None, help="Draft content (for --save)")
        action_parser.add_argument("--file", default=None, help="File path with draft content (for --save)")
        action_parser.add_argument("--clear", action="store_true", help="Clear draft (for --save)")

    elif resource == "run" and action == "list":
        action_parser.add_argument("--session", default=None, help="Optional session ID")
    elif resource == "run" and action in {"show", "retry", "resume", "cancel"}:
        action_parser.add_argument("--run", default=None, help="Run ID")

    elif resource == "checker" and action == "run":
        action_parser.add_argument("--session", required=True, help="Session ID")
        action_parser.add_argument("--artifact", required=True, help="Artifact ID to check")
        action_parser.add_argument("--no-citations", action="store_true", help="Skip citation checking")
        action_parser.add_argument("--no-ai", action="store_true", help="Skip AI pattern detection")
        action_parser.add_argument("--no-flow", action="store_true", help="Skip flow analysis")
    elif resource == "checker" and action == "status":
        action_parser.add_argument("run_id", help="Checker run ID")
    elif resource == "checker" and action == "results":
        action_parser.add_argument("run_id", help="Checker run ID")

    elif resource == "citalio" and action == "run":
        action_parser.add_argument("--session", default=None, help="Session ID")
        action_parser.add_argument("--artifact", default=None, help="Artifact ID as input")
        action_parser.add_argument("--text", default=None, help="Inline text input")
        action_parser.add_argument("--min-confidence", type=float, default=0.5, help="Min relevance confidence")
        action_parser.add_argument("--max-citations-per-sentence", type=int, default=3, help="Maximum citations to insert per sentence")
        action_parser.add_argument("--include-common-knowledge", action="store_true", help="Also suggest citations for COMMON sentences")
    elif resource == "citalio" and action == "status":
        action_parser.add_argument("run_id", help="Citalio run ID")
    elif resource == "citalio" and action == "results":
        action_parser.add_argument("run_id", help="Citalio run ID")

    elif resource == "proliferomaxima" and action == "run":
        action_parser.add_argument("--library-path", default=None, help="Override parsed markdown directory")
        action_parser.add_argument("--max-files", type=int, default=None, help="Limit number of markdown files")
        action_parser.add_argument("--max-items", type=int, default=None, help="Limit number of references")
        action_parser.add_argument("--wait", action="store_true", help="Wait for completion and fetch results")
    elif resource == "proliferomaxima" and action in {"status", "results"}:
        action_parser.add_argument("run_id", help="Proliferomaxima run ID")

    elif resource == "vf" and action == "generate":
        action_parser.add_argument("--paper-id", required=True, help="Canonical paper ID, e.g. Power_1997")
        action_parser.add_argument("--metadata-json", default=None, help="Metadata JSON string")
        action_parser.add_argument("--abstract", default=None, help="Abstract text")
        action_parser.add_argument("--abstract-file", default=None, help="Path to abstract text file")
        action_parser.add_argument("--full-text", default=None, help="Full text for in-library generation")
        action_parser.add_argument("--full-text-file", default=None, help="Path to full text file")
        action_parser.add_argument("--external", action="store_true", help="Mark profile as external (in_library=false)")
        action_parser.add_argument("--agent", default="helper", help="Agent name: helper/dr-xiaolei/asst-xiaolei")
    elif resource == "vf" and action == "batch":
        action_parser.add_argument("--file", required=True, help="JSON file containing {'items':[...]} batch payload")
    elif resource == "vf" and action == "lookup":
        action_parser.add_argument("--paper-id", default=None, help="Lookup exact profile by paper ID")
        action_parser.add_argument("--author", default=None, help="Author surname for exact match")
        action_parser.add_argument("--year", type=int, default=None, help="Publication year for exact match")
    elif resource == "vf" and action == "stats":
        pass
    elif resource == "vf" and action == "list":
        action_parser.add_argument("--limit", type=int, default=50, help="List limit")
        action_parser.add_argument("--offset", type=int, default=0, help="List offset")
    elif resource == "vf" and action == "delete":
        action_parser.add_argument("--paper-id", required=True, help="Delete profile by paper ID")
    elif resource == "vf" and action == "sync":
        action_parser.add_argument("--library-path", default=None, help="Parsed library path")
        action_parser.add_argument("--agent", default="helper", help="Agent name: helper/dr-xiaolei/asst-xiaolei")
        action_parser.add_argument("--dry-run", action="store_true", help="Preview new papers only")
        action_parser.add_argument("--concurrency", type=int, default=1, help="Concurrency (reserved, currently sequential)")

    elif resource == "log" and action == "stream":
        action_parser.add_argument("--level", default=None, help="Filter by log level (DEBUG, INFO, WARNING, ERROR)")
        action_parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    elif resource == "log" and action == "recent":
        action_parser.add_argument("--limit", type=int, default=100, help="Number of log entries (default: 100)")
        action_parser.add_argument("--level", default=None, help="Filter by log level")


def build_parser() -> argparse.ArgumentParser:
    parser = CLIArgumentParser(
        prog="agentb",
        description="Agent-B-Academic CLI",
    )
    _add_global_flags(parser)

    root_subparsers = parser.add_subparsers(dest="resource", metavar="<resource>")
    root_subparsers.required = True

    for resource, actions in _resource_actions().items():
        resource_parser = root_subparsers.add_parser(resource, help=f"{resource} operations")
        _add_global_flags(resource_parser)
        action_subparsers = resource_parser.add_subparsers(dest="action", metavar="<action>")
        action_subparsers.required = True

        for action in actions:
            action_parser = action_subparsers.add_parser(action, help=f"{action} {resource}")
            # Duplicate global flags at action-level so flags work in any position.
            _add_global_flags(action_parser)
            _configure_action_parser(resource, action, action_parser)
            action_parser.set_defaults(handler=_handler_for(resource, action))

    return parser


def _argv_wants_json(argv: Optional[list[str]]) -> bool:
    if not argv:
        return False
    return "--json" in argv


def _arg_value(argv: list[str], flag: str, default: str | None = None) -> str | None:
    if flag not in argv:
        return default
    try:
        idx = len(argv) - 1 - argv[::-1].index(flag)
        if idx + 1 < len(argv):
            return argv[idx + 1]
    except Exception:
        pass
    return default


def _apply_aliases(arg_list: list[str]) -> list[str]:
    if not arg_list:
        return arg_list

    resource_alias = {
        "sess": "session",
        "ctx": "context",
        "src": "source",
        "pers": "persona",
        "art": "artifact",
        "rn": "run",
        "stat": "status",
    }

    action_alias_common = {
        "ls": "list",
        "cur": "current",
        "del": "delete",
    }

    out = list(arg_list)

    # Replace first non-flag token as resource alias.
    for i, tok in enumerate(out):
        if not tok.startswith("-"):
            out[i] = resource_alias.get(tok, tok)
            # Next non-flag token is action.
            for j in range(i + 1, len(out)):
                if not out[j].startswith("-"):
                    act = out[j]
                    if out[i] == "source" and act == "rm":
                        out[j] = "remove"
                    elif out[i] == "artifact" and act == "rm":
                        out[j] = "delete"
                    else:
                        out[j] = action_alias_common.get(act, act)
                    break
            break

    return out


def _command_name(args: argparse.Namespace) -> str:
    resource = getattr(args, "resource", "unknown")
    action = getattr(args, "action", "unknown")
    return f"{resource}:{action}"


def _trace_ids(args: argparse.Namespace, payload: dict | None = None) -> tuple[str | None, str | None]:
    session_id = getattr(args, "session", None)
    run_id = getattr(args, "run", None)

    if isinstance(payload, dict):
        data = payload.get("data") or {}
        if isinstance(data, dict):
            session_id = data.get("session_id") or session_id
            run_id = data.get("run_id") or run_id
            run_obj = data.get("run")
            if isinstance(run_obj, dict):
                run_id = run_obj.get("id") or run_id
                session_id = run_obj.get("session_id") or session_id

    return session_id, run_id


def _requires_session_for_write(args: argparse.Namespace) -> bool:
    resource = getattr(args, "resource", "")
    action = getattr(args, "action", "")

    if resource == "chat" and action == "send":
        return True
    if resource == "source" and action == "add":
        return True
    if resource == "artifact" and action == "create":
        return True
    if resource == "persona" and action == "select":
        return True
    if resource == "context" and action in {"set", "get", "clear"} and getattr(args, "scope", None) == "session":
        return True

    return False


def _resolve_session_defaults(args: argparse.Namespace, mode_value: str) -> None:
    # Only operate when command supports session and it is currently missing.
    if not hasattr(args, "session"):
        return
    if getattr(args, "session", None):
        return

    write_requires_session = _requires_session_for_write(args)
    use_current = bool(getattr(args, "use_current_session", False))

    from .state_store import load_state

    state = load_state()
    current = state.get("current_session_id")

    if use_current or mode_value == "interactive":
        if current:
            args.session = current
            return
        if write_requires_session:
            raise CLIBusinessError(code="SESSION_CURRENT_NOT_SET", message="Current session is not set")
        return

    # automation mode strict rule
    if mode_value == "automation" and write_requires_session:
        raise CLIBusinessError(
            code="SESSION_REQUIRED_AUTOMATION",
            message="--session is required in automation mode for this write command",
            details={"hint": "pass --session or --use-current-session"},
        )


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    raw_arg_list = argv if argv is not None else sys.argv[1:]
    arg_list = _apply_aliases(raw_arg_list)
    args: argparse.Namespace | None = None
    command = "unknown:unknown"
    log_format = "text"
    log_file = None
    to_stderr = True

    try:
        if "--automation" in arg_list and "--interactive" in arg_list:
            raise CLIBusinessError(
                code="CLI_MODE_CONFLICT",
                message="--automation and --interactive cannot be used together",
            )

        args = parser.parse_args(arg_list)
        # Normalize duplicated global flags regardless of argument position.
        if _argv_wants_json(arg_list):
            args.json = True
        if "--yes" in arg_list:
            args.yes = True
        if "--automation" in arg_list:
            args.automation = True
        if "--interactive" in arg_list:
            args.interactive = True
        if "--quiet" in arg_list:
            args.quiet = True
        if "--use-current-session" in arg_list:
            args.use_current_session = True

        mode = detect_mode(
            force_automation=bool(getattr(args, "automation", False)),
            force_interactive=bool(getattr(args, "interactive", False)),
            stdin_isatty=sys.stdin.isatty(),
        )
        _resolve_session_defaults(args, mode.value)

        command = _command_name(args)
        log_format = _arg_value(arg_list, "--log-format", "text") or "text"
        log_file = _arg_value(arg_list, "--log-file", None)
        # Suppress stderr logs in JSON mode to avoid PowerShell treating stderr as errors
        to_stderr = "--quiet" not in arg_list and "--json" not in arg_list

        api_version = _arg_value(arg_list, "--api-version", str(getattr(args, "api_version", "1")))
        if api_version not in {"1", "1.0"}:
            raise CLIBusinessError(
                code="CLI_API_VERSION_UNSUPPORTED",
                message="Unsupported api version",
                details={"requested": api_version, "supported": ["1", "1.0"]},
            )

        session_id, run_id = _trace_ids(args)
        emit_log(
            log_format=log_format,
            log_file=log_file,
            command=command,
            event="command_start",
            level="info",
            session_id=session_id,
            run_id=run_id,
            to_stderr=to_stderr,
        )

        if "--simulate-system-error" in arg_list:
            raise CLISystemError(
                code="CLI_SIMULATED_SYSTEM_ERROR",
                message="Simulated runtime/system failure",
                details="Used for contract and exit-code verification",
            )

        handler: Handler = getattr(args, "handler", noop_handler)
        payload = handler(args)

        session_id, run_id = _trace_ids(args, payload)
        emit_log(
            log_format=log_format,
            log_file=log_file,
            command=command,
            event="command_end",
            level="info",
            session_id=session_id,
            run_id=run_id,
            to_stderr=to_stderr,
        )

        _print(args, payload)
        return 0

    except CLIError as exc:
        payload = error_envelope(code=exc.code, message=exc.message, details=exc.details)
        wants_json = _argv_wants_json(arg_list)

        session_id = getattr(args, "session", None) if args else None
        run_id = getattr(args, "run", None) if args else None
        emit_log(
            log_format=log_format,
            log_file=log_file,
            command=command,
            event="command_error",
            level="error",
            session_id=session_id,
            run_id=run_id,
            to_stderr=to_stderr,
        )

        if wants_json:
            print(render_json(payload))
        else:
            print(f"[ERROR] {exc.code}: {exc.message}", file=sys.stderr)
        return exc.exit_code

    except Exception as exc:
        payload = error_envelope(
            code="CLI_UNHANDLED_EXCEPTION",
            message="Unhandled system error",
            details=str(exc),
        )
        wants_json = _argv_wants_json(arg_list)

        session_id = getattr(args, "session", None) if args else None
        run_id = getattr(args, "run", None) if args else None
        emit_log(
            log_format=log_format,
            log_file=log_file,
            command=command,
            event="command_error",
            level="error",
            session_id=session_id,
            run_id=run_id,
            to_stderr=to_stderr,
        )

        if wants_json:
            print(render_json(payload))
        else:
            print(f"[ERROR] CLI_UNHANDLED_EXCEPTION: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
