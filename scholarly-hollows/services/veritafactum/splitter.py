"""Sentence splitter with academic-aware post-processing.

Uses spaCy for initial sentence boundary detection, then applies
rules specific to academic writing (et al., citations, abbreviations).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

from app.logging_config import get_logger

logger = get_logger("checker.splitter")

# Lazy-loaded spaCy model
_nlp = None


def _get_nlp():
    """Lazy-load spaCy model with graceful degradation."""
    global _nlp
    if _nlp is not None:
        return _nlp
    try:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
        return _nlp
    except Exception as e:
        logger.warning(f"spaCy not available/usable, falling back to regex splitter: {e}")
        return None


@dataclass
class Sentence:
    """A single sentence extracted from academic text."""
    id: int
    text: str
    start_offset: int
    end_offset: int
    paragraph_id: int
    existing_citations: List[str] = field(default_factory=list)
    is_footnote: bool = False


# Pattern to find inline citations like (Author, Year) or (Author et al., Year)
CITATION_PATTERN = re.compile(
    r'\((?:[A-Z][a-zA-Z\-\']+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-zA-Z\-\']+))?'
    r'(?:,\s*\d{4}[a-z]?)(?:;\s*[A-Z][a-zA-Z\-\']+(?:\s+(?:et\s+al\.|&\s+[A-Z][a-zA-Z\-\']+))?'
    r'(?:,\s*\d{4}[a-z]?))*)\)'
)

# Abbreviations that should NOT cause sentence breaks
ABBREVIATIONS = re.compile(
    r'\b(et\s+al|e\.g|i\.e|cf|viz|vs|approx|etc|ibid|supra|infra)\.\s',
    re.IGNORECASE,
)


def _extract_citations(text: str) -> List[str]:
    """Extract parenthetical citations from a sentence."""
    return CITATION_PATTERN.findall(text)


def _fallback_split(text: str) -> List[str]:
    """Regex-based sentence splitter as fallback when spaCy is unavailable."""
    # Split on sentence-ending punctuation followed by space + capital letter
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
    return [p.strip() for p in parts if p.strip()]


def _merge_fragments(sentences: List[str]) -> List[str]:
    """Merge sentence fragments that were incorrectly split.
    
    Handles cases like splits after 'et al.', 'e.g.', 'i.e.', etc.
    Also merges very short fragments (< 20 chars) that are likely continuations.
    """
    if not sentences:
        return sentences

    merged: List[str] = []
    buffer = ""

    for sent in sentences:
        if buffer:
            # Check if the previous buffer ended with an abbreviation
            if ABBREVIATIONS.search(buffer):
                buffer = buffer + " " + sent if not buffer.endswith(" ") else buffer + sent
                continue
            # Check if this fragment is very short and doesn't start with a capital
            if len(sent) < 20 and sent and not sent[0].isupper():
                buffer = buffer + " " + sent
                continue
            merged.append(buffer)
            buffer = sent
        else:
            buffer = sent

    if buffer:
        merged.append(buffer)

    return merged


def _check_unbalanced_parens(text: str) -> bool:
    """Check if text has unbalanced parentheses (indicating a bad split inside parens)."""
    depth = 0
    for ch in text:
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
    return depth != 0


def split_sentences(text: str) -> List[Sentence]:
    """Split academic text into sentences with metadata.
    
    Args:
        text: The full text to split.
        
    Returns:
        List of Sentence objects with offsets and citation info.
    """
    if not text or not text.strip():
        return []

    nlp = _get_nlp()

    # Split into paragraphs first
    paragraphs = re.split(r'\n\s*\n', text)
    
    all_sentences: List[Sentence] = []
    sentence_id = 0
    global_offset = 0

    for para_id, paragraph in enumerate(paragraphs):
        paragraph = paragraph.strip()
        if not paragraph:
            # Track offset for empty paragraphs
            global_offset = text.find(paragraph, global_offset) + len(paragraph)
            continue

        # Find this paragraph's position in the original text
        para_start = text.find(paragraph, global_offset)
        if para_start == -1:
            para_start = global_offset

        # Get raw sentences
        if nlp is not None:
            doc = nlp(paragraph)
            raw_sents = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        else:
            raw_sents = _fallback_split(paragraph)

        # Post-processing: merge fragments
        processed = _merge_fragments(raw_sents)

        # Second pass: merge sentences with unbalanced parentheses
        final_sents: List[str] = []
        i = 0
        while i < len(processed):
            sent = processed[i]
            # If unbalanced parens, merge with next sentence
            while _check_unbalanced_parens(sent) and i + 1 < len(processed):
                i += 1
                sent = sent + " " + processed[i]
            final_sents.append(sent)
            i += 1

        # Create Sentence objects
        search_start = para_start
        for sent_text in final_sents:
            # Find position in original text
            sent_start = text.find(sent_text, search_start)
            if sent_start == -1:
                sent_start = search_start
            sent_end = sent_start + len(sent_text)

            citations = _extract_citations(sent_text)

            all_sentences.append(Sentence(
                id=sentence_id,
                text=sent_text,
                start_offset=sent_start,
                end_offset=sent_end,
                paragraph_id=para_id,
                existing_citations=citations,
                is_footnote=False,
            ))
            sentence_id += 1
            search_start = sent_end

        global_offset = para_start + len(paragraph)

    return all_sentences
