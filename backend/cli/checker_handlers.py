from __future__ import annotations

import os
import time

import httpx

from .contract import CLIBusinessError, success_envelope


def _load_env_config():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env_vars[key.strip()] = val.strip()
    return env_vars


_env = _load_env_config()
BACKEND_API_URL = os.getenv("AGENTB_API_URL") or _env.get("AGENTB_API_URL", "http://localhost:8001")

_TYPE_ICONS = {
    "CITE_NEEDED": "🔴",
    "COMMON": "🟢",
    "OWN_EMPIRICAL": "🔵",
    "OWN_CONTRIBUTION": "🟡",
}

_FLAG_ICONS = {
    "MISATTRIBUTED": "⚠️",
    "AI_PATTERN": "🤖",
    "FLOW_ISSUE": "🔗",
}


def _format_annotations(annotations: list[dict]) -> str:
    lines = []
    for i, ann in enumerate(annotations, 1):
        ann_type = ann.get("type", "UNKNOWN")
        icon = _TYPE_ICONS.get(ann_type, "⚪")
        confidence = ann.get("confidence", 0)
        text = ann.get("text", ann.get("sentence", ""))
        flags = ann.get("flags", [])

        lines.append(f"\n  [{i}] {icon} {ann_type} (confidence: {confidence:.0%})")
        if text:
            preview = text[:120] + ("..." if len(text) > 120 else "")
            lines.append(f"      \"{preview}\"")

        for flag in flags:
            flag_name = flag if isinstance(flag, str) else flag.get("type", str(flag))
            flag_icon = _FLAG_ICONS.get(flag_name, "❓")
            lines.append(f"      {flag_icon} {flag_name}")

        suggestion = ann.get("suggestion") or ann.get("suggestions")
        if suggestion:
            if isinstance(suggestion, list):
                for s in suggestion:
                    lines.append(f"      💡 {s}")
            else:
                lines.append(f"      💡 {suggestion}")

    return "\n".join(lines)


def _print_status(status_data: dict, quiet: bool = False) -> None:
    if quiet:
        return
    status = status_data.get("status", "unknown")
    progress = status_data.get("progress", 0)
    stage = status_data.get("stage", "")
    bar = "█" * int(progress * 20) + "░" * (20 - int(progress * 20))
    extra = f" — {stage}" if stage else ""
    print(f"\r  [{bar}] {progress:.0%} {status}{extra}", end="", flush=True)


def checker_run(args):
    if not args.session:
        raise CLIBusinessError(code="CHECKER_SESSION_REQUIRED", message="--session is required")
    if not args.artifact:
        raise CLIBusinessError(code="CHECKER_ARTIFACT_REQUIRED", message="--artifact is required")

    quiet = getattr(args, "quiet", False)

    # 1. Fetch artifact content
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BACKEND_API_URL}/api/v1/artifacts/{args.artifact}/content")
        if r.status_code != 200:
            raise CLIBusinessError(
                code="ARTIFACT_FETCH_FAILED",
                message=f"Failed to fetch artifact content (HTTP {r.status_code})",
                details=r.text[:300],
            )
        # Content endpoint may return text/markdown or JSON
        content_type = r.headers.get("content-type", "")
        if "json" in content_type:
            content_data = r.json()
            text = content_data.get("text") or content_data.get("content") or ""
        else:
            text = r.text

    if not text.strip():
        raise CLIBusinessError(code="ARTIFACT_EMPTY", message="Artifact has no content to check")

    # 2. Submit checker run
    options = {
        "check_citations": not getattr(args, "no_citations", False),
        "check_ai": not getattr(args, "no_ai", False),
        "check_flow": not getattr(args, "no_flow", False),
    }

    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            f"{BACKEND_API_URL}/api/v1/checker/run",
            json={"text": text, "artifact_id": args.artifact, "options": options},
        )
        if r.status_code not in (200, 201, 202):
            raise CLIBusinessError(
                code="CHECKER_SUBMIT_FAILED",
                message=f"Failed to submit checker run (HTTP {r.status_code})",
                details=r.text[:300],
            )
        run_data = r.json()
        run_id = run_data.get("run_id") or run_data.get("id")

    if not run_id:
        raise CLIBusinessError(code="CHECKER_NO_RUN_ID", message="No run_id returned from checker")

    if not quiet:
        print(f"  Checker run started: {run_id}")

    # 3. Poll until completed/failed
    with httpx.Client(timeout=30.0) as client:
        while True:
            time.sleep(3)
            r = client.get(f"{BACKEND_API_URL}/api/v1/checker/status/{run_id}")
            if r.status_code != 200:
                raise CLIBusinessError(
                    code="CHECKER_POLL_FAILED",
                    message=f"Failed to poll checker status (HTTP {r.status_code})",
                )
            status_data = r.json()
            status = status_data.get("status", "unknown")

            _print_status(status_data, quiet)

            if status == "completed":
                if not quiet:
                    print()  # newline after progress bar
                break
            elif status == "failed":
                if not quiet:
                    print()
                error_msg = status_data.get("error", "Unknown error")
                raise CLIBusinessError(code="CHECKER_RUN_FAILED", message=f"Checker run failed: {error_msg}")

    # 4. Fetch results
    r = client.get(f"{BACKEND_API_URL}/api/v1/checker/results/{run_id}")
    if r.status_code != 200:
        raise CLIBusinessError(
            code="CHECKER_RESULTS_FAILED",
            message=f"Failed to fetch checker results (HTTP {r.status_code})",
        )
    results = r.json()

    # Display summary
    annotations = results.get("annotations", [])
    summary = results.get("summary", {})

    if not quiet:
        print(f"\n  ✅ Checker completed — {len(annotations)} annotations")
        if summary:
            for k, v in summary.items():
                print(f"     {k}: {v}")
        if annotations:
            print(_format_annotations(annotations))

    return success_envelope(
        result="completed",
        data={"run_id": run_id, "annotations_count": len(annotations), "summary": summary, "annotations": annotations},
    )


def checker_status(args):
    run_id = args.run_id
    if not run_id:
        raise CLIBusinessError(code="CHECKER_RUN_ID_REQUIRED", message="run_id is required")

    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BACKEND_API_URL}/api/v1/checker/status/{run_id}")
        if r.status_code != 200:
            raise CLIBusinessError(
                code="CHECKER_STATUS_FAILED",
                message=f"Failed to fetch checker status (HTTP {r.status_code})",
                details=r.text[:300],
            )
        status_data = r.json()

    quiet = getattr(args, "quiet", False)
    if not quiet:
        status = status_data.get("status", "unknown")
        progress = status_data.get("progress", 0)
        stage = status_data.get("stage", "")
        print(f"  Run: {run_id}")
        print(f"  Status: {status}")
        print(f"  Progress: {progress:.0%}")
        if stage:
            print(f"  Stage: {stage}")

    return success_envelope(result="ok", data=status_data)


def checker_results(args):
    run_id = args.run_id
    if not run_id:
        raise CLIBusinessError(code="CHECKER_RUN_ID_REQUIRED", message="run_id is required")

    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BACKEND_API_URL}/api/v1/checker/results/{run_id}")
        if r.status_code != 200:
            raise CLIBusinessError(
                code="CHECKER_RESULTS_FAILED",
                message=f"Failed to fetch checker results (HTTP {r.status_code})",
                details=r.text[:300],
            )
        results = r.json()

    annotations = results.get("annotations", [])
    summary = results.get("summary", {})

    quiet = getattr(args, "quiet", False)
    if not quiet:
        print(f"\n  Results for run: {run_id}")
        print(f"  Total annotations: {len(annotations)}")
        if summary:
            for k, v in summary.items():
                print(f"  {k}: {v}")
        if annotations:
            print(_format_annotations(annotations))
        else:
            print("  No annotations found.")

    return success_envelope(result="ok", data=results)
