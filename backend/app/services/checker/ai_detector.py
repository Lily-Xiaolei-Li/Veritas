"""AI writing pattern detector (rule-based).

Uses regex patterns to detect common AI-generated text markers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

from app.logging_config import get_logger

logger = get_logger("checker.ai_detector")


@dataclass
class AIFlag:
    """A detected AI writing pattern."""
    pattern_name: str
    matched_text: str
    note: str
    severity: str  # low, medium, high


# Pattern definitions from design doc Appendix B
AI_PATTERNS = {
    "triple_structure": {
        "regex": re.compile(r"\b(first|second|third|firstly|secondly|thirdly)\b", re.IGNORECASE),
        "note": "Excessive use of numbered enumerations",
        "severity": "low",
    },
    "hedge_stacking": {
        "regex": re.compile(
            r"(it is (important|worth|crucial) to (note|mention|highlight|emphasize))",
            re.IGNORECASE,
        ),
        "note": "Filler phrase — adds no content",
        "severity": "medium",
    },
    "moreover_chain": {
        "regex": re.compile(r"^(Moreover|Furthermore|Additionally|In addition),", re.MULTILINE),
        "note": "Generic transition — consider removing or replacing with content-specific connector",
        "severity": "medium",
    },
    "ai_adjectives": {
        "regex": re.compile(
            r"\b(crucial|pivotal|paramount|groundbreaking|transformative|indispensable|noteworthy|compelling)\b",
            re.IGNORECASE,
        ),
        "note": "Overused AI-favoured adjective",
        "severity": "low",
    },
    "ai_verbs": {
        "regex": re.compile(
            r"\b(delve|underscore|shed light|navigate|unpack|leverage|foster)\b",
            re.IGNORECASE,
        ),
        "note": "Stereotypical AI verb choice",
        "severity": "medium",
    },
    "empty_topic_sentence": {
        "regex": re.compile(
            r"^(This (section|paper|study|analysis|article) (examines|explores|investigates|addresses|discusses))",
            re.IGNORECASE,
        ),
        "note": "Generic topic sentence — consider leading with the actual argument",
        "severity": "low",
    },
    "in_conclusion_opener": {
        "regex": re.compile(r"^In (conclusion|summary|sum),", re.IGNORECASE),
        "note": "Clichéd opener — the section heading already signals this",
        "severity": "low",
    },
    "generic_hedging": {
        "regex": re.compile(r"\b(may|might|could)\s+(potentially|possibly|arguably)\b", re.IGNORECASE),
        "note": "Double hedging — pick one qualifier",
        "severity": "medium",
    },
    "filler_phrases": {
        "regex": re.compile(
            r"\b(in the context of|in terms of|with respect to|in light of)\b",
            re.IGNORECASE,
        ),
        "note": "Wordy filler phrase",
        "severity": "low",
    },
}


def detect_ai_patterns(sentence_text: str) -> List[AIFlag]:
    """Detect AI writing patterns in a single sentence.
    
    Args:
        sentence_text: The sentence to check.
        
    Returns:
        List of AIFlag objects for detected patterns.
    """
    flags: List[AIFlag] = []

    for pattern_name, config in AI_PATTERNS.items():
        regex = config["regex"]
        matches = regex.findall(sentence_text)
        if matches:
            # Get the first match text
            matched = matches[0] if isinstance(matches[0], str) else matches[0][0] if matches[0] else ""
            flags.append(AIFlag(
                pattern_name=pattern_name,
                matched_text=str(matched),
                note=config["note"],
                severity=config["severity"],
            ))

    return flags


def detect_all(sentences_texts: List[str]) -> List[List[AIFlag]]:
    """Detect AI patterns for a list of sentences.
    
    Returns:
        List of AIFlag lists, one per input sentence.
    """
    return [detect_ai_patterns(text) for text in sentences_texts]
