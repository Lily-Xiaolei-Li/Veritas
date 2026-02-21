"""Claim and term extraction via LLM.

Batches 5-10 sentences per LLM call to extract claims, key terms,
named scholars, and search queries for RAG lookup.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, List, Optional

from app.logging_config import get_logger

from .splitter import Sentence

logger = get_logger("checker.extractor")


@dataclass
class SentenceAnalysis:
    """Extracted analysis for a single sentence."""
    sentence: Sentence
    claims: List[str] = field(default_factory=list)
    key_terms: List[str] = field(default_factory=list)
    named_scholars: List[str] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)
    is_common: bool = False
    is_own: bool = False


EXTRACTION_SYSTEM_PROMPT = """You are an academic citation analyst specialising in accounting, auditing, and social science research.

For each sentence below, extract:

1. **Claims**: What factual or theoretical claims does this sentence make? 
   (A claim is any statement that could be true or false, supported or unsupported)
2. **Key Terms**: Technical terms, named concepts, or jargon that may originate from specific scholars
3. **Named Scholars**: Any scholars mentioned by name (with or without citation)
4. **Search Queries**: 2-3 semantic search queries to find relevant sources in an academic library

If the sentence is clearly common knowledge (e.g., "Australia is a country"), set is_common=true.
If the sentence is clearly the author's own argument (e.g., "We argue that..."), set is_own=true.

Output as a JSON array. Each element corresponds to one input sentence (same order).
Example element:
{
  "claims": ["auditing enables organisational conduct"],
  "key_terms": ["audit", "organisational conduct"],
  "named_scholars": ["Power"],
  "search_queries": ["auditing organisational conduct framing", "Power audit society"],
  "is_common": false,
  "is_own": false
}"""

# Type alias for the LLM call function
LLMCallFn = Callable[[str, str], Coroutine[Any, Any, str]]

BATCH_SIZE = 8


async def extract_claims_batch(
    sentences: List[Sentence],
    llm_call: LLMCallFn,
    batch_size: int = BATCH_SIZE,
) -> List[SentenceAnalysis]:
    """Extract claims and terms from sentences in batches.
    
    Args:
        sentences: List of Sentence objects to analyse.
        llm_call: Async function(system_prompt, user_prompt) -> str response.
        batch_size: Number of sentences per LLM call.
        
    Returns:
        List of SentenceAnalysis objects (same order as input).
    """
    all_analyses: List[SentenceAnalysis] = []

    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i + batch_size]

        # Build user prompt
        lines = []
        for j, sent in enumerate(batch):
            lines.append(f"[{j + 1}] \"{sent.text}\"")
        user_prompt = "Analyse these sentences:\n\n" + "\n".join(lines) + "\n\nOutput JSON array only."

        try:
            response_text = await llm_call(EXTRACTION_SYSTEM_PROMPT, user_prompt)
            parsed = _parse_json_array(response_text, len(batch))

            for j, sent in enumerate(batch):
                if j < len(parsed):
                    item = parsed[j]
                    all_analyses.append(SentenceAnalysis(
                        sentence=sent,
                        claims=item.get("claims", []),
                        key_terms=item.get("key_terms", []),
                        named_scholars=item.get("named_scholars", []),
                        search_queries=item.get("search_queries", []),
                        is_common=item.get("is_common", False),
                        is_own=item.get("is_own", False),
                    ))
                else:
                    all_analyses.append(SentenceAnalysis(sentence=sent))

        except Exception as e:
            logger.error(f"Extraction batch failed: {e}", exc_info=True)
            # Return empty analyses for failed batch
            for sent in batch:
                all_analyses.append(SentenceAnalysis(sentence=sent))

    return all_analyses


def _parse_json_array(text: str, expected_len: int) -> List[dict]:
    """Parse JSON array from LLM response, handling markdown fences."""
    text = text.strip()
    # Remove markdown code fences
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

    # Try to find JSON array in the text
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            result = json.loads(text[start:end + 1])
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    logger.warning(f"Failed to parse LLM JSON response, returning empty results")
    return [{} for _ in range(expected_len)]
