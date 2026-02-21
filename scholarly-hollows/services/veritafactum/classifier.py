"""Sentence classification via LLM.

Classifies each sentence as CITE_NEEDED / COMMON / OWN_EMPIRICAL / OWN_CONTRIBUTION
and verifies existing citations against RAG results.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, List, Optional

from app.logging_config import get_logger

from .extractor import SentenceAnalysis
from .rag_searcher import SentenceRAGResults
from .splitter import Sentence

logger = get_logger("checker.classifier")

# Type alias for the LLM call function
LLMCallFn = Callable[[str, str], Coroutine[Any, Any, str]]


@dataclass
class CitationVerification:
    """Verification status of an existing citation."""
    citation: str
    status: str  # VERIFIED, MISATTRIBUTED, NOT_IN_LIBRARY
    note: str = ""


@dataclass
class ClassificationResult:
    """Classification result for a single sentence."""
    sentence_id: int
    type: str  # CITE_NEEDED, COMMON, OWN_EMPIRICAL, OWN_CONTRIBUTION
    confidence: str  # HIGH, MEDIUM, LOW
    reasoning: str = ""
    suggested_citations: List[str] = field(default_factory=list)
    citation_verification: List[CitationVerification] = field(default_factory=list)
    section_reference: Optional[str] = None  # For OWN_EMPIRICAL


CLASSIFICATION_SYSTEM_PROMPT = """You are a senior academic reviewer at a top accounting journal (AOS, AAAJ, or similar).

Your task: Classify this sentence and check its citations.

CLASSIFY into exactly ONE type:
- CITE_NEEDED: This sentence makes a claim from prior literature that requires citation.
  → Which citation(s) should be added? Use RAG results if relevant.
- COMMON: This is field-level common knowledge. No citation needed.
- OWN_EMPIRICAL: This reports the author's own fieldwork data or findings. 
  → Which section of the paper does this come from?
- OWN_CONTRIBUTION: This is the author's original theoretical argument.
  → No citation needed, but verify it reads as authorial voice.

ALSO CHECK:
- For each existing citation: Is it correctly attributed based on RAG results? 
  (VERIFIED / MISATTRIBUTED / NOT_IN_LIBRARY)
- Confidence: HIGH (certain) / MEDIUM (likely but debatable) / LOW (uncertain)

Output valid JSON only:
{
  "type": "CITE_NEEDED|COMMON|OWN_EMPIRICAL|OWN_CONTRIBUTION",
  "confidence": "HIGH|MEDIUM|LOW",
  "reasoning": "Brief explanation",
  "suggested_citations": ["Author (Year) - reason"],
  "citation_verification": [{"citation": "Power (2021)", "status": "VERIFIED|MISATTRIBUTED|NOT_IN_LIBRARY", "note": "..."}],
  "section_reference": null
}"""


def _build_user_prompt(
    sentence: Sentence,
    prev_sentence: Optional[Sentence],
    next_sentence: Optional[Sentence],
    rag_results: SentenceRAGResults,
) -> str:
    """Build the user prompt for classification."""
    parts = ["CONTEXT:"]
    
    if prev_sentence:
        parts.append(f'- Previous sentence: "{prev_sentence.text}"')
    else:
        parts.append("- Previous sentence: [start of text]")
    
    parts.append(f'- >>> CURRENT SENTENCE: "{sentence.text}" <<<')
    
    if next_sentence:
        parts.append(f'- Next sentence: "{next_sentence.text}"')
    else:
        parts.append("- Next sentence: [end of text]")
    
    if sentence.existing_citations:
        parts.append(f"- Existing citations in this sentence: {sentence.existing_citations}")
    else:
        parts.append("- Existing citations: none")
    
    parts.append("")
    parts.append("RAG LIBRARY SEARCH RESULTS (most relevant sources found):")
    
    if rag_results.results:
        for i, r in enumerate(rag_results.results[:5]):
            source_info = r.source or "Unknown"
            parts.append(f'[{i + 1}] {source_info} — "{r.text[:200]}..." (similarity: {r.score:.2f})')
    else:
        parts.append("[No relevant sources found in library]")
    
    return "\n".join(parts)


async def classify_sentence(
    sentence: Sentence,
    prev_sentence: Optional[Sentence],
    next_sentence: Optional[Sentence],
    rag_results: SentenceRAGResults,
    llm_call: LLMCallFn,
) -> ClassificationResult:
    """Classify a single sentence using LLM with RAG context."""
    user_prompt = _build_user_prompt(sentence, prev_sentence, next_sentence, rag_results)

    try:
        response_text = await llm_call(CLASSIFICATION_SYSTEM_PROMPT, user_prompt)
        result = _parse_classification(response_text)
        result.sentence_id = sentence.id
        return result
    except Exception as e:
        logger.error(f"Classification failed for sentence {sentence.id}: {e}", exc_info=True)
        return ClassificationResult(
            sentence_id=sentence.id,
            type="COMMON",
            confidence="LOW",
            reasoning=f"Classification failed: {e}",
        )


def _parse_classification(text: str) -> ClassificationResult:
    """Parse LLM classification response."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                return ClassificationResult(
                    sentence_id=-1,
                    type="COMMON",
                    confidence="LOW",
                    reasoning="Failed to parse LLM response",
                )
        else:
            return ClassificationResult(
                sentence_id=-1,
                type="COMMON",
                confidence="LOW",
                reasoning="Failed to parse LLM response",
            )

    verifications = []
    for v in data.get("citation_verification", []):
        if isinstance(v, dict):
            verifications.append(CitationVerification(
                citation=v.get("citation", ""),
                status=v.get("status", "NOT_IN_LIBRARY"),
                note=v.get("note", ""),
            ))

    return ClassificationResult(
        sentence_id=-1,  # Will be set by caller
        type=data.get("type", "COMMON"),
        confidence=data.get("confidence", "LOW"),
        reasoning=data.get("reasoning", ""),
        suggested_citations=data.get("suggested_citations", []),
        citation_verification=verifications,
        section_reference=data.get("section_reference"),
    )


async def classify_all_sentences(
    sentences: List[Sentence],
    rag_results_map: Dict[int, SentenceRAGResults],
    llm_call: LLMCallFn,
    progress_callback: Optional[Callable] = None,
) -> List[ClassificationResult]:
    """Classify all sentences sequentially (each needs unique context)."""
    results: List[ClassificationResult] = []

    for i, sent in enumerate(sentences):
        prev_sent = sentences[i - 1] if i > 0 else None
        next_sent = sentences[i + 1] if i + 1 < len(sentences) else None
        rag = rag_results_map.get(sent.id, SentenceRAGResults(sentence_id=sent.id))

        result = await classify_sentence(sent, prev_sent, next_sent, rag, llm_call)
        results.append(result)

        if progress_callback:
            await progress_callback(current=i + 1, total=len(sentences), step="classification")

    return results
