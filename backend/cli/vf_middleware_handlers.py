from __future__ import annotations

import json
import os

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


def vf_generate(args):
    if not args.paper_id:
        raise CLIBusinessError(code="VF_PAPER_ID_REQUIRED", message="--paper-id is required")

    metadata = {}
    if args.metadata_json:
        try:
            metadata = json.loads(args.metadata_json)
        except Exception as e:
            raise CLIBusinessError(code="VF_INVALID_METADATA_JSON", message=str(e))

    abstract = args.abstract or ""
    if args.abstract_file:
        with open(args.abstract_file, encoding="utf-8") as f:
            abstract = f.read()

    full_text = args.full_text
    if args.full_text_file:
        with open(args.full_text_file, encoding="utf-8") as f:
            full_text = f.read()

    with httpx.Client(timeout=300.0) as client:
        r = client.post(
            f"{BACKEND_API_URL}/api/v1/vf/generate",
            json={
                "paper_id": args.paper_id,
                "metadata": metadata,
                "abstract": abstract,
                "full_text": full_text,
                "in_library": not bool(args.external),
                "agent": args.agent or "helper",
            },
        )

    if r.status_code not in (200, 201):
        raise CLIBusinessError(code="VF_GENERATE_FAILED", message=f"HTTP {r.status_code}", details=r.text[:500])

    data = r.json()
    if not getattr(args, "quiet", False):
        print(f"✅ Generated profile: {data.get('paper_id')} ({data.get('chunks_upserted')} chunks)")

    return success_envelope(result="ok", data=data)


def vf_batch(args):
    if not args.file:
        raise CLIBusinessError(code="VF_BATCH_FILE_REQUIRED", message="--file is required")

    with open(args.file, encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        payload = {"items": payload}

    with httpx.Client(timeout=1800.0) as client:
        r = client.post(f"{BACKEND_API_URL}/api/v1/vf/batch", json=payload)

    if r.status_code != 200:
        raise CLIBusinessError(code="VF_BATCH_FAILED", message=f"HTTP {r.status_code}", details=r.text[:500])

    data = r.json()
    return success_envelope(result="ok", data=data)


def vf_lookup(args):
    params = {}
    if args.paper_id:
        params["paper_id"] = args.paper_id
    if args.author:
        params["author"] = args.author
    if args.year:
        params["year"] = args.year

    with httpx.Client(timeout=60.0) as client:
        r = client.get(f"{BACKEND_API_URL}/api/v1/vf/lookup", params=params)

    if r.status_code != 200:
        raise CLIBusinessError(code="VF_LOOKUP_FAILED", message=f"HTTP {r.status_code}", details=r.text[:500])

    return success_envelope(result="ok", data=r.json())


def vf_stats(args):
    with httpx.Client(timeout=30.0) as client:
        r = client.get(f"{BACKEND_API_URL}/api/v1/vf/stats")
    if r.status_code != 200:
        raise CLIBusinessError(code="VF_STATS_FAILED", message=f"HTTP {r.status_code}", details=r.text[:500])
    return success_envelope(result="ok", data=r.json())


def vf_list(args):
    with httpx.Client(timeout=30.0) as client:
        r = client.get(
            f"{BACKEND_API_URL}/api/v1/vf/list",
            params={"limit": args.limit or 50, "offset": args.offset or 0},
        )
    if r.status_code != 200:
        raise CLIBusinessError(code="VF_LIST_FAILED", message=f"HTTP {r.status_code}", details=r.text[:500])
    return success_envelope(result="ok", data=r.json())


def vf_delete(args):
    if not args.paper_id:
        raise CLIBusinessError(code="VF_PAPER_ID_REQUIRED", message="--paper-id is required")

    with httpx.Client(timeout=30.0) as client:
        r = client.delete(f"{BACKEND_API_URL}/api/v1/vf/{args.paper_id}")
    if r.status_code != 200:
        raise CLIBusinessError(code="VF_DELETE_FAILED", message=f"HTTP {r.status_code}", details=r.text[:500])
    return success_envelope(result="ok", data=r.json())


def vf_sync(args):
    payload = {
        "library_path": args.library_path,
        "agent": args.agent or "helper",
        "dry_run": bool(args.dry_run),
    }

    with httpx.Client(timeout=3600.0) as client:
        with client.stream("POST", f"{BACKEND_API_URL}/api/v1/vf/sync", json=payload) as r:
            if r.status_code != 200:
                raise CLIBusinessError(code="VF_SYNC_FAILED", message=f"HTTP {r.status_code}", details=r.text[:500])

            last_event = None
            for line in r.iter_lines():
                if not line:
                    continue
                if line.startswith("data:"):
                    raw = line[5:].strip()
                    try:
                        evt = json.loads(raw)
                        last_event = evt
                    except Exception:
                        continue

                    status = evt.get("status")
                    if status == "processing":
                        print(f"[{evt.get('processed', 0)}/{evt.get('total', 0)}] Processing: {evt.get('current_paper', '')}")
                    elif status == "dry_run":
                        print(f"Dry run: {evt.get('count', 0)} new papers")
                    elif status == "error":
                        print(f"Error on {evt.get('current_paper')}: {evt.get('error')}")
                    elif status == "done":
                        print(f"Done: success={evt.get('success')} failed={evt.get('failed')} skipped={evt.get('skipped')}")

    return success_envelope(result="ok", data=last_event or {"status": "unknown"})
