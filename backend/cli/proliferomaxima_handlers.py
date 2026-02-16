from __future__ import annotations

import os
import time

import httpx

from .contract import CLIBusinessError, success_envelope


def _load_env_config():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env_vars[key.strip()] = val.strip()
    return env_vars


_env = _load_env_config()
BACKEND_API_URL = os.getenv("AGENTB_API_URL") or _env.get("AGENTB_API_URL", "http://localhost:8001")


def proliferomaxima_run(args):
    payload = {
        "library_path": args.library_path,
        "max_files": args.max_files,
        "max_items": args.max_items,
    }

    with httpx.Client(timeout=60.0) as client:
        r = client.post(f"{BACKEND_API_URL}/api/v1/proliferomaxima/run", json=payload)
        if r.status_code not in (200, 201, 202):
            raise CLIBusinessError(code="PROLIFEROMAXIMA_SUBMIT_FAILED", message=f"Submit failed (HTTP {r.status_code})", details=r.text[:300])
        data = r.json()

    run_id = data.get("run_id")
    if not run_id:
        raise CLIBusinessError(code="PROLIFEROMAXIMA_NO_RUN_ID", message="No run_id returned")

    if not getattr(args, "quiet", False):
        print(f"  Proliferomaxima run started: {run_id}")

    if not args.wait:
        return success_envelope(result="queued", data=data)

    with httpx.Client(timeout=30.0) as client:
        while True:
            time.sleep(2)
            status_resp = client.get(f"{BACKEND_API_URL}/api/v1/proliferomaxima/status/{run_id}")
            if status_resp.status_code != 200:
                raise CLIBusinessError(code="PROLIFEROMAXIMA_POLL_FAILED", message=f"Status poll failed (HTTP {status_resp.status_code})")
            s = status_resp.json()
            st = s.get("status")
            prog = s.get("progress") or {}
            if not getattr(args, "quiet", False):
                print(f"\r  {st} {prog.get('step', '')} {prog.get('current', 0)}/{prog.get('total', 0)}", end="", flush=True)

            if st == "completed":
                if not getattr(args, "quiet", False):
                    print()
                break
            if st == "failed":
                if not getattr(args, "quiet", False):
                    print()
                raise CLIBusinessError(code="PROLIFEROMAXIMA_RUN_FAILED", message=s.get("error") or "run failed")

        rr = client.get(f"{BACKEND_API_URL}/api/v1/proliferomaxima/results/{run_id}")
        if rr.status_code != 200:
            raise CLIBusinessError(code="PROLIFEROMAXIMA_RESULTS_FAILED", message=f"Results fetch failed (HTTP {rr.status_code})")
        results = rr.json()

    return success_envelope(result="completed", data=results)


def proliferomaxima_status(args):
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BACKEND_API_URL}/api/v1/proliferomaxima/status/{args.run_id}")
        if r.status_code != 200:
            raise CLIBusinessError(code="PROLIFEROMAXIMA_STATUS_FAILED", message=f"Status fetch failed (HTTP {r.status_code})", details=r.text[:300])
    return success_envelope(result="ok", data=r.json())


def proliferomaxima_results(args):
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BACKEND_API_URL}/api/v1/proliferomaxima/results/{args.run_id}")
        if r.status_code != 200:
            raise CLIBusinessError(code="PROLIFEROMAXIMA_RESULTS_FAILED", message=f"Results fetch failed (HTTP {r.status_code})", details=r.text[:300])
    return success_envelope(result="ok", data=r.json())
