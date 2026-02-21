from __future__ import annotations

from typing import List

from .citation_searcher import CitationCandidate


class CitationInserter:
    """Generate suggested sentence with citations appended."""

    @staticmethod
    def insert(sentence: str, candidates: List[CitationCandidate], max_citations: int = 3) -> str:
        if not candidates:
            return sentence
        refs = [c.citation_text for c in candidates[:max_citations] if c.citation_text]
        if not refs:
            return sentence

        clean = sentence.strip()
        end = "."
        if clean.endswith((".", "!", "?")):
            end = clean[-1]
            clean = clean[:-1].rstrip()

        joined = "; ".join(refs)
        return f"{clean} {joined}{end}"
