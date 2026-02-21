"""Main orchestrator for the Sentence-Level Academic Checker.

Coordinates all steps: split → extract → RAG search → classify → AI detect → flow check → report.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional
from uuid import uuid4

try:
    from app.logging_config import get_logger
    from app.services.vf_middleware import profile_searcher as rag_searcher
except ImportError:
    from ...logging_config import get_logger
    # Fallback: stub rag_searcher if not available
    rag_searcher = None

from . import ai_detector, classifier, extractor, flow_checker, report_generator, splitter

logger = get_logger("checker.engine")

# Type alias for progress callback
ProgressCallback = Optional[Callable[..., Coroutine[Any, Any, None]]]

# Type alias for LLM call function
LLMCallFn = Callable[[str, str], Coroutine[Any, Any, str]]


def _load_gateway_config() -> tuple[str, str]:
    """Load Gateway URL and auth token from backend .env."""
    import os
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, val = line.partition("=")
                    env_vars[key.strip()] = val.strip()
    url = os.getenv("XIAOLEI_GATEWAY_URL") or env_vars.get("XIAOLEI_GATEWAY_URL", "http://localhost:18789")
    token = os.getenv("XIAOLEI_AUTH_TOKEN") or env_vars.get("XIAOLEI_AUTH_TOKEN", "")
    return url, token


_GATEWAY_URL, _GATEWAY_TOKEN = _load_gateway_config()


async def _default_llm_call(system_prompt: str, user_prompt: str) -> str:
    """Default LLM call via OpenClaw Gateway.
    
    Uses auth token from backend .env for authentication.
    """
    import httpx

    headers = {"Content-Type": "application/json"}
    if _GATEWAY_TOKEN:
        headers["Authorization"] = f"Bearer {_GATEWAY_TOKEN}"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{_GATEWAY_URL}/v1/chat/completions",
                headers=headers,
                json={
                    "model": "anthropic/claude-sonnet-4-20250514",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 4096,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"OpenClaw Gateway call failed: {e}")
        raise


class CheckerRun:
    """Represents a single checker run with all its state."""

    def __init__(
        self,
        run_id: str,
        text: str,
        artifact_id: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ):
        self.run_id = run_id
        self.text = text
        self.artifact_id = artifact_id or str(uuid4())
        self.options = options or {
            "check_citations": True,
            "check_ai": True,
            "check_flow": True,
        }
        self.status = "queued"
        self.progress = {"current": 0, "total": 0, "step": ""}
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None


async def run_checker(
    text: str,
    artifact_id: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
    llm_call: Optional[LLMCallFn] = None,
    progress_callback: ProgressCallback = None,
) -> Dict[str, Any]:
    """Run the full sentence checker pipeline.
    
    Args:
        text: The academic text to check.
        artifact_id: Optional artifact ID for tracking.
        options: Checker options (check_citations, check_ai, check_flow).
        llm_call: Optional custom LLM call function. Defaults to OpenClaw Gateway.
        progress_callback: Optional async callback for progress updates.
        
    Returns:
        Structured JSON report dict.
    """
    run_id = f"checker-{uuid4().hex[:8]}"
    opts = options or {"check_citations": True, "check_ai": True, "check_flow": True}
    call_llm = llm_call or _default_llm_call

    async def _progress(current: int = 0, total: int = 0, step: str = ""):
        if progress_callback:
            await progress_callback(current=current, total=total, step=step)

    # Step 1: Sentence splitting
    logger.info(f"[{run_id}] Step 1: Splitting sentences...")
    await _progress(step="splitting")
    sentences = splitter.split_sentences(text)
    total = len(sentences)
    logger.info(f"[{run_id}] Found {total} sentences")
    await _progress(current=0, total=total, step="splitting_done")

    if not sentences:
        return report_generator.generate_json_report(
            sentences=[], classifications=[], ai_flags=[],
            flow_checks=[], rag_results=[], run_id=run_id, artifact_id=artifact_id,
        )

    # Step 2: Claim/term extraction
    logger.info(f"[{run_id}] Step 2: Extracting claims and terms...")
    await _progress(step="extraction")
    analyses = await extractor.extract_claims_batch(sentences, call_llm)

    # Step 3: RAG search
    if opts.get("check_citations", True):
        logger.info(f"[{run_id}] Step 3: RAG search...")
        await _progress(step="rag_search")
        rag_results_list = await rag_searcher.search_all_sentences(analyses)
    else:
        rag_results_list = [rag_searcher.SentenceRAGResults(sentence_id=s.id) for s in sentences]

    rag_results_map = {r.sentence_id: r for r in rag_results_list}

    # Step 4: Classification
    if opts.get("check_citations", True):
        logger.info(f"[{run_id}] Step 4: Classifying sentences...")
        classifications = await classifier.classify_all_sentences(
            sentences, rag_results_map, call_llm,
            progress_callback=progress_callback,
        )
    else:
        classifications = [
            classifier.ClassificationResult(sentence_id=s.id, type="COMMON", confidence="LOW")
            for s in sentences
        ]

    # Step 5: AI pattern detection
    if opts.get("check_ai", True):
        logger.info(f"[{run_id}] Step 5: Detecting AI patterns...")
        await _progress(step="ai_detection")
        ai_flags = ai_detector.detect_all([s.text for s in sentences])
    else:
        ai_flags = [[] for _ in sentences]

    # Step 6: Flow check
    if opts.get("check_flow", True):
        logger.info(f"[{run_id}] Step 6: Checking flow...")
        await _progress(step="flow_check")
        flow_checks = await flow_checker.check_all_flow(sentences, call_llm)
    else:
        flow_checks = [flow_checker.FlowCheck(sentence_id=s.id) for s in sentences]

    # Step 7: Generate reports
    logger.info(f"[{run_id}] Step 7: Generating report...")
    await _progress(step="report_generation")

    json_report = report_generator.generate_json_report(
        sentences, classifications, ai_flags, flow_checks,
        rag_results_list, run_id, artifact_id,
    )

    markdown_report = report_generator.generate_markdown_report(
        sentences, classifications, ai_flags, flow_checks,
        rag_results_list, run_id,
    )

    json_report["markdown_report"] = markdown_report

    logger.info(f"[{run_id}] Complete! {total} sentences analysed.")
    await _progress(current=total, total=total, step="completed")

    return json_report
