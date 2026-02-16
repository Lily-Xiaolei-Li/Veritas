from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, List

from app.logging_config import get_logger

from .citation_searcher import CitationCandidate

logger = get_logger("citalio.relevance_scorer")

LLMCallFn = Callable[[str, str], Coroutine[Any, Any, str]]


@dataclass
class RelevanceDecision:
    relevant: bool
    confidence: float
    reason: str


SYSTEM_PROMPT = """You are an academic citation expert. Evaluate whether a candidate paper directly supports a sentence.
Return strict JSON only:
{
  \"relevant\": true,
  \"confidence\": 0.0,
  \"reason\": \"short reason\"
}
Rules:
- confidence in [0,1]
- high confidence only when directly supporting the claim
- be conservative
"""


class RelevanceScorer:
    def __init__(self, llm_call: LLMCallFn):
        self.llm_call = llm_call

    async def score_one(self, sentence: str, candidate: CitationCandidate) -> RelevanceDecision:
        user_prompt = (
            f"Sentence: {sentence}\n"
            f"Candidate paper: {candidate.title} ({', '.join(candidate.authors)}, {candidate.year})\n"
            f"cited_for: {candidate.cited_for}\n"
        )
        try:
            raw = await self.llm_call(SYSTEM_PROMPT, user_prompt)
            data = self._parse_json(raw)
            confidence = float(data.get("confidence", 0.0))
            confidence = max(0.0, min(1.0, confidence))
            return RelevanceDecision(
                relevant=bool(data.get("relevant", False)),
                confidence=confidence,
                reason=str(data.get("reason", ""))[:500],
            )
        except Exception as e:
            logger.warning(f"LLM relevance scoring failed, fallback to vector score: {e}")
            fallback = max(0.0, min(1.0, candidate.relevance_score))
            return RelevanceDecision(relevant=fallback >= 0.6, confidence=fallback, reason="fallback from vector relevance")

    @staticmethod
    def _parse_json(raw: str) -> dict:
        txt = raw.strip()
        if txt.startswith("```"):
            txt = txt.split("\n", 1)[-1]
            if txt.endswith("```"):
                txt = txt[:-3]
            txt = txt.strip()
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            s, e = txt.find("{"), txt.rfind("}")
            if s != -1 and e != -1 and e > s:
                try:
                    return json.loads(txt[s : e + 1])
                except Exception:
                    pass
        return {}

    async def score(self, sentence: str, candidates: List[CitationCandidate]) -> List[CitationCandidate]:
        out: List[CitationCandidate] = []
        for c in candidates:
            decision = await self.score_one(sentence, c)
            c.confidence = decision.confidence
            c.reason = decision.reason
            if decision.relevant:
                out.append(c)
        out.sort(key=lambda x: x.confidence, reverse=True)
        return out
