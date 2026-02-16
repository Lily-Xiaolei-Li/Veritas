from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from app.logging_config import get_logger
from app.services.vf_middleware.profile_store import VFProfileStore

logger = get_logger("citalio.citation_searcher")


@dataclass
class CitationCandidate:
    paper_id: str
    authors: List[str] = field(default_factory=list)
    year: int | None = None
    title: str = ""
    cited_for: str = ""
    relevance_score: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    citation_text: str = ""


class CitationSearcher:
    """Search VF profiles with a strong preference for cited_for chunks."""

    def __init__(self, store: VFProfileStore | None = None):
        self.store = store or VFProfileStore()

    @staticmethod
    def _author_year_text(authors: List[str], year: int | None) -> str:
        if not authors:
            return "(Unknown, n.d.)"
        first = authors[0]
        surname = first.split(",")[0].strip() if "," in first else first.split()[-1]
        if len(authors) > 2:
            label = f"{surname} et al."
        elif len(authors) == 2:
            second = authors[1].split(",")[0].strip() if "," in authors[1] else authors[1].split()[-1]
            label = f"{surname} & {second}"
        else:
            label = surname
        return f"({label}, {year if year else 'n.d.'})"

    def _merge_rank(self, primary: List[dict], secondary: List[dict], top_k: int) -> List[CitationCandidate]:
        by_paper: Dict[str, CitationCandidate] = {}

        def _apply(rows: List[dict], boost: float):
            for row in rows:
                paper_id = str(row.get("paper_id") or "")
                if not paper_id:
                    continue
                meta = row.get("meta") or {}
                authors = meta.get("authors") if isinstance(meta.get("authors"), list) else []
                year = meta.get("year") if isinstance(meta.get("year"), int) else None
                title = str(meta.get("title") or paper_id)
                score = float(row.get("score") or 0.0) * boost

                current = by_paper.get(paper_id)
                if current is None:
                    by_paper[paper_id] = CitationCandidate(
                        paper_id=paper_id,
                        authors=[str(a) for a in authors],
                        year=year,
                        title=title,
                        cited_for=str(row.get("text") or "")[:1800],
                        relevance_score=score,
                    )
                else:
                    if score > current.relevance_score:
                        current.relevance_score = score
                    if str(row.get("chunk_id")) == "cited_for" and row.get("text"):
                        current.cited_for = str(row.get("text"))[:1800]

        _apply(primary, boost=1.0)
        _apply(secondary, boost=0.9)

        ranked = sorted(by_paper.values(), key=lambda c: c.relevance_score, reverse=True)
        for c in ranked:
            c.citation_text = self._author_year_text(c.authors, c.year)
        return ranked[:top_k]

    def search(self, sentence_text: str, top_k: int = 5) -> List[CitationCandidate]:
        try:
            cited_for_results = self.store.semantic_search(sentence_text, limit=12, chunk_id="cited_for")
            theory_results = self.store.semantic_search(sentence_text, limit=8, chunk_id="theory")
            contrib_results = self.store.semantic_search(sentence_text, limit=8, chunk_id="contributions")
            return self._merge_rank(cited_for_results, theory_results + contrib_results, top_k=top_k)
        except Exception as e:
            logger.error(f"Citalio search failed: {e}", exc_info=True)
            return []
