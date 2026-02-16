"""Flow and transition analysis via LLM.

Checks sentence-to-sentence coherence within paragraphs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.logging_config import get_logger

from .splitter import Sentence

logger = get_logger("checker.flow_checker")

LLMCallFn = Callable[[str, str], Coroutine[Any, Any, str]]


@dataclass
class FlowCheck:
    """Flow analysis for a single sentence."""
    sentence_id: int
    prev_connection: str = "STRONG"  # STRONG, ADEQUATE, WEAK, MISSING
    suggestion: Optional[str] = None
    topic_shift: bool = False


FLOW_SYSTEM_PROMPT = """You are an academic writing flow analyst. Analyse the transitions between consecutive sentences in this paragraph.

For each transition (from sentence N to N+1), rate:
- STRONG: Natural logical progression
- ADEQUATE: Acceptable but could be smoother
- WEAK: Abrupt shift, needs transitional language
- MISSING: No logical connection, possible restructuring needed

Also note if there's an abrupt topic shift.

Output a JSON array with one entry per transition:
[
  {"from": 1, "to": 2, "rating": "STRONG|ADEQUATE|WEAK|MISSING", "suggestion": null, "topic_shift": false},
  ...
]"""


async def check_paragraph_flow(
    sentences: List[Sentence],
    llm_call: LLMCallFn,
) -> List[FlowCheck]:
    """Check flow between sentences in a single paragraph."""
    if len(sentences) < 2:
        return [FlowCheck(sentence_id=s.id) for s in sentences]

    # Build prompt
    lines = []
    for i, sent in enumerate(sentences):
        lines.append(f"[{i + 1}] \"{sent.text}\"")
    user_prompt = "Analyse transitions in this paragraph:\n\n" + "\n".join(lines)

    try:
        response = await llm_call(FLOW_SYSTEM_PROMPT, user_prompt)
        transitions = _parse_flow_response(response)

        # Build FlowCheck for each sentence
        results: List[FlowCheck] = []
        transition_map: Dict[int, dict] = {}
        for t in transitions:
            to_idx = t.get("to", 0) - 1  # Convert to 0-indexed
            if 0 <= to_idx < len(sentences):
                transition_map[to_idx] = t

        for i, sent in enumerate(sentences):
            if i == 0:
                results.append(FlowCheck(sentence_id=sent.id))
            else:
                t = transition_map.get(i, {})
                results.append(FlowCheck(
                    sentence_id=sent.id,
                    prev_connection=t.get("rating", "ADEQUATE"),
                    suggestion=t.get("suggestion"),
                    topic_shift=t.get("topic_shift", False),
                ))

        return results

    except Exception as e:
        logger.error(f"Flow check failed: {e}", exc_info=True)
        return [FlowCheck(sentence_id=s.id) for s in sentences]


def _parse_flow_response(text: str) -> List[dict]:
    """Parse flow check JSON response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    return []


async def check_all_flow(
    sentences: List[Sentence],
    llm_call: LLMCallFn,
) -> List[FlowCheck]:
    """Check flow for all sentences, grouped by paragraph."""
    # Group by paragraph
    paragraphs: Dict[int, List[Sentence]] = {}
    for sent in sentences:
        paragraphs.setdefault(sent.paragraph_id, []).append(sent)

    all_checks: Dict[int, FlowCheck] = {}

    for para_id in sorted(paragraphs.keys()):
        para_sents = paragraphs[para_id]
        checks = await check_paragraph_flow(para_sents, llm_call)
        for check in checks:
            all_checks[check.sentence_id] = check

    # Return in sentence order
    return [all_checks.get(s.id, FlowCheck(sentence_id=s.id)) for s in sentences]
