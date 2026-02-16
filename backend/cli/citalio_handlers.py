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


def citalio_run(args):
    text = args.text
    if not text and args.artifact:
        with httpx.Client(timeout=30.0) as client:
            r = client.get(f"{BACKEND_API_URL}/api/v1/artifacts/{args.artifact}/content")
            if r.status_code != 200:
                raise CLIBusinessError(code="ARTIFACT_FETCH_FAILED", message=f"Failed to fetch artifact (HTTP {r.status_code})")
            ctype = r.headers.get("content-type", "")
            if "json" in ctype:
                payload = r.json()
                text = payload.get("text") or payload.get("content") or ""
            else:
                text = r.text

    if not text or not text.strip():
        raise CLIBusinessError(code="CITALIO_TEXT_REQUIRED", message="Provide --text or --artifact with non-empty content")

    options = {
        "min_confidence": args.min_confidence,
        "max_citations_per_sentence": args.max_citations_per_sentence,
        "include_common_knowledge": bool(args.include_common_knowledge),
    }

    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            f"{BACKEND_API_URL}/api/v1/citalio/run",
            json={"text": text, "session_id": args.session, "options": options},
        )
        if r.status_code not in (200, 201, 202):
            raise CLIBusinessError(code="CITALIO_SUBMIT_FAILED", message=f"Submit failed (HTTP {r.status_code})", details=r.text[:300])
        run_id = r.json().get("run_id")

    if not run_id:
        raise CLIBusinessError(code="CITALIO_NO_RUN_ID", message="No run_id returned")

    if not getattr(args, "quiet", False):
        print(f"  Citalio run started: {run_id}")

    with httpx.Client(timeout=30.0) as client:
        while True:
            time.sleep(2)
            status_resp = client.get(f"{BACKEND_API_URL}/api/v1/citalio/status/{run_id}")
            if status_resp.status_code != 200:
                raise CLIBusinessError(code="CITALIO_POLL_FAILED", message=f"Status poll failed (HTTP {status_resp.status_code})")
            data = status_resp.json()
            status = data.get("status")
            if not getattr(args, "quiet", False):
                prog = data.get("progress") or {}
                print(f"\r  {status} {prog.get('step', '')} {prog.get('current', 0)}/{prog.get('total', 0)}", end="", flush=True)

            if status == "completed":
                if not getattr(args, "quiet", False):
                    print()
                break
            if status == "failed":
                if not getattr(args, "quiet", False):
                    print()
                raise CLIBusinessError(code="CITALIO_RUN_FAILED", message=data.get("error") or "Citalio run failed")

        res = client.get(f"{BACKEND_API_URL}/api/v1/citalio/results/{run_id}")
        if res.status_code != 200:
            raise CLIBusinessError(code="CITALIO_RESULTS_FAILED", message=f"Results fetch failed (HTTP {res.status_code})")
        results = res.json()

    if not getattr(args, "quiet", False):
        summary = (results.get("results") or {}).get("summary", {})
        print(f"  ✅ done: auto={summary.get('auto_cited', 0)} maybe={summary.get('maybe_cited', 0)} manual={summary.get('manual_needed', 0)}")

    return success_envelope(result="completed", data=results)


def citalio_status(args):
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BACKEND_API_URL}/api/v1/citalio/status/{args.run_id}")
        if r.status_code != 200:
            raise CLIBusinessError(code="CITALIO_STATUS_FAILED", message=f"Status fetch failed (HTTP {r.status_code})", details=r.text[:300])
        payload = r.json()
    if not getattr(args, "quiet", False):
        print(payload)
    return success_envelope(result="ok", data=payload)


def citalio_results(args):
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BACKEND_API_URL}/api/v1/citalio/results/{args.run_id}")
        if r.status_code != 200:
            raise CLIBusinessError(code="CITALIO_RESULTS_FAILED", message=f"Results fetch failed (HTTP {r.status_code})", details=r.text[:300])
        payload = r.json()
    if not getattr(args, "quiet", False):
        summary = (payload.get("results") or {}).get("summary", {})
        print(summary)
    return success_envelope(result="ok", data=payload)
