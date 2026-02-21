"""
Citalio Manual Search - 手动模式搜索 VF Store

Provides manual citation search with:
- Custom filters (year, paper_type, method, keywords, journal, etc.)
- Chunk type selection (cited_for, theory, contributions, etc.)
- Full matched paragraph display (not just keywords)
- cite_intext and cite_full fields for easy insertion
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.logging_config import get_logger
from app.services.vf_middleware.profile_store import VFProfileStore

logger = get_logger("citalio.manual_search")

# Valid chunk types for search
VALID_CHUNK_TYPES = [
    "cited_for",
    "theory",
    "contributions",
    "literature",
    "abstract",
    "key_concepts",
    "research_questions",
]


@dataclass
class ManualSearchResult:
    """A single result from manual Citalio search."""
    paper_id: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    title: str = ""
    journal: Optional[str] = None
    matched_chunk_type: str = ""
    matched_text: str = ""
    relevance_score: float = 0.0
    cite_intext: str = ""
    cite_full: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)


class CitalioManualSearcher:
    """Manual citation search with filters."""

    def __init__(self, store: Optional[VFProfileStore] = None):
        self.store = store or VFProfileStore()

    def search(
        self,
        query: str,
        chunk_types: List[str] = None,
        limit: int = 10,
        filters: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search VF Store with query and filters.
        
        Args:
            query: The text to search for (selected sentence)
            chunk_types: Which chunk types to search (default: cited_for, theory, contributions)
            limit: Max results to return
            filters: Dict with year_min, year_max, paper_type, primary_method, keywords, journal, etc.
        
        Returns:
            List of results with matched paragraphs and citation info
        """
        if chunk_types is None:
            chunk_types = ["cited_for", "theory", "contributions"]
        
        # Validate chunk types
        chunk_types = [c for c in chunk_types if c in VALID_CHUNK_TYPES]
        if not chunk_types:
            chunk_types = ["cited_for"]
        
        filters = filters or {}
        
        # Pre-encode query ONCE to avoid repeated encoding
        logger.info(f"Encoding query: {query[:50]}...")
        query_vector = self.store.encode_query(query)
        logger.info("Query encoded, starting searches...")
        
        # Collect results from all chunk types
        all_results: List[Dict[str, Any]] = []
        
        for chunk_type in chunk_types:
            try:
                logger.info(f"Searching chunk_type: {chunk_type}")
                # Search this chunk type (get more than needed, will filter later)
                # Pass pre-computed vector to avoid re-encoding
                raw_results = self.store.semantic_search(
                    query=query,
                    limit=limit * 3,  # Get more to allow for filtering
                    chunk_id=chunk_type,
                    query_vector=query_vector,  # Reuse encoded vector!
                )
                
                for r in raw_results:
                    # Apply filters
                    if not self._passes_filters(r, filters):
                        continue
                    
                    meta = r.get("meta", {})
                    authors = meta.get("authors", [])
                    year = meta.get("year")
                    title = meta.get("title", r.get("paper_id", ""))
                    journal = meta.get("journal")
                    
                    # Generate citation formats
                    cite_intext = self._format_intext_citation(authors, year)
                    cite_full = self._format_full_reference(meta)
                    
                    all_results.append({
                        "paper_id": r.get("paper_id", ""),
                        "authors": authors if isinstance(authors, list) else [],
                        "year": year if isinstance(year, int) else None,
                        "title": title,
                        "journal": journal,
                        "matched_chunk_type": chunk_type,
                        "matched_text": r.get("text", ""),  # Full paragraph
                        "relevance_score": float(r.get("score", 0.0)),
                        "cite_intext": cite_intext,
                        "cite_full": cite_full,
                        "meta": meta,
                    })
            except Exception as e:
                logger.warning(f"Error searching chunk type {chunk_type}: {e}")
                continue
        
        # Sort by relevance and deduplicate by paper_id (keep highest score)
        seen_papers: Dict[str, Dict[str, Any]] = {}
        for r in all_results:
            paper_id = r["paper_id"]
            if paper_id not in seen_papers or r["relevance_score"] > seen_papers[paper_id]["relevance_score"]:
                seen_papers[paper_id] = r
        
        # Sort by relevance score descending
        sorted_results = sorted(seen_papers.values(), key=lambda x: x["relevance_score"], reverse=True)
        
        return sorted_results[:limit]

    def _passes_filters(self, result: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if a result passes all filters."""
        if not filters:
            return True
        
        meta = result.get("meta", {})
        
        # Year range filter
        year = meta.get("year")
        if filters.get("year_min") is not None:
            if not isinstance(year, int) or year < filters["year_min"]:
                return False
        if filters.get("year_max") is not None:
            if not isinstance(year, int) or year > filters["year_max"]:
                return False
        
        # Paper type filter
        if filters.get("paper_type"):
            paper_type = str(meta.get("paper_type", "")).lower()
            if filters["paper_type"].lower() not in paper_type:
                return False
        
        # Primary method filter
        if filters.get("primary_method"):
            primary_method = str(meta.get("primary_method", "")).lower()
            if filters["primary_method"].lower() not in primary_method:
                return False
        
        # Keywords filter (match any)
        if filters.get("keywords"):
            author_kw = [str(k).lower() for k in (meta.get("keywords_author") or [])]
            inferred_kw = [str(k).lower() for k in (meta.get("keywords_inferred") or [])]
            all_kw = set(author_kw + inferred_kw)
            filter_kw = [k.lower() for k in filters["keywords"]]
            if not any(any(fk in kw for kw in all_kw) for fk in filter_kw):
                return False
        
        # Journal filter (partial match)
        if filters.get("journal"):
            journal = str(meta.get("journal", "")).lower()
            if filters["journal"].lower() not in journal:
                return False
        
        # Authors filter (partial match on any author)
        if filters.get("authors"):
            paper_authors = [str(a).lower() for a in (meta.get("authors") or [])]
            filter_authors = [a.lower() for a in filters["authors"]]
            if not any(any(fa in pa for pa in paper_authors) for fa in filter_authors):
                return False
        
        # In library filter
        if filters.get("in_library") is not None:
            in_lib = result.get("in_library", meta.get("in_library", False))
            if bool(in_lib) != bool(filters["in_library"]):
                return False
        
        # Empirical context filter (partial match)
        if filters.get("empirical_context"):
            context = str(meta.get("empirical_context", "")).lower()
            if filters["empirical_context"].lower() not in context:
                return False
        
        return True

    def _format_intext_citation(self, authors: List[str], year: Optional[int]) -> str:
        """Format in-text citation: (Author, Year) or (Author et al., Year)."""
        if not authors:
            return "(Unknown, n.d.)"
        
        # Extract surname from first author
        first = authors[0]
        if "," in first:
            surname = first.split(",")[0].strip()
        else:
            parts = first.split()
            surname = parts[-1] if parts else first
        
        if len(authors) > 2:
            label = f"{surname} et al."
        elif len(authors) == 2:
            second = authors[1]
            if "," in second:
                surname2 = second.split(",")[0].strip()
            else:
                parts2 = second.split()
                surname2 = parts2[-1] if parts2 else second
            label = f"{surname} & {surname2}"
        else:
            label = surname
        
        year_str = str(year) if year else "n.d."
        return f"({label}, {year_str})"

    def _format_full_reference(self, meta: Dict[str, Any]) -> str:
        """
        Format full Harvard-style reference.
        
        Example: Power, M. (2003). Auditing and the production of legitimacy. 
                 Accounting, Organizations and Society, 28(4), 379-394.
        """
        authors = meta.get("authors", [])
        year = meta.get("year")
        title = meta.get("title", "")
        journal = meta.get("journal")
        volume = meta.get("volume")
        issue = meta.get("issue")
        pages = meta.get("pages")
        
        # Format authors: "Surname, F., Surname2, F. & Surname3, F."
        if not authors:
            author_str = "Unknown"
        elif len(authors) == 1:
            author_str = self._format_author_harvard(authors[0])
        elif len(authors) == 2:
            author_str = f"{self._format_author_harvard(authors[0])} & {self._format_author_harvard(authors[1])}"
        else:
            # First n-1 authors with commas, last with &
            formatted = [self._format_author_harvard(a) for a in authors]
            author_str = ", ".join(formatted[:-1]) + " & " + formatted[-1]
        
        # Year
        year_str = f"({year})" if year else "(n.d.)"
        
        # Title (sentence case, no quotes for journal articles)
        title_str = title.strip().rstrip(".")
        
        # Build reference
        ref_parts = [f"{author_str} {year_str}. {title_str}."]
        
        if journal:
            journal_part = f" {journal}"
            if volume:
                journal_part += f", {volume}"
                if issue:
                    journal_part += f"({issue})"
            if pages:
                journal_part += f", {pages}"
            journal_part += "."
            ref_parts.append(journal_part)
        
        return "".join(ref_parts)

    def _format_author_harvard(self, author: str) -> str:
        """Format single author for Harvard reference: 'Surname, F.'"""
        author = author.strip()
        if not author:
            return "Unknown"
        
        if "," in author:
            # Already in "Surname, FirstName" format
            parts = author.split(",", 1)
            surname = parts[0].strip()
            given = parts[1].strip() if len(parts) > 1 else ""
            initials = "".join(n[0].upper() + "." for n in given.split() if n)
            return f"{surname}, {initials}" if initials else surname
        else:
            # "FirstName Surname" format
            parts = author.split()
            if len(parts) == 1:
                return parts[0]
            surname = parts[-1]
            initials = "".join(n[0].upper() + "." for n in parts[:-1] if n)
            return f"{surname}, {initials}" if initials else surname

    def get_filter_options(self) -> Dict[str, Any]:
        """
        Get available filter options from VF Store for UI dropdowns.
        
        Returns distinct values for paper_type, primary_method, journals, etc.
        """
        try:
            # Get a sample of profiles to extract available options
            profiles = self.store.list_profiles(limit=500)
            
            paper_types: set = set()
            methods: set = set()
            journals: set = set()
            years: set = set()
            contexts: set = set()
            
            for p in profiles:
                # We only have basic info from list_profiles
                # For full options, we'd need to query more
                if p.get("year"):
                    years.add(p["year"])
            
            # Get more detailed info by sampling some profiles
            sample_ids = [p["paper_id"] for p in profiles[:100]]
            for paper_id in sample_ids:
                try:
                    profile = self.store.get_profile(paper_id)
                    if not profile:
                        continue
                    meta = profile.get("meta", {})
                    
                    if meta.get("paper_type"):
                        paper_types.add(meta["paper_type"])
                    if meta.get("primary_method"):
                        methods.add(meta["primary_method"])
                    if meta.get("journal"):
                        journals.add(meta["journal"])
                    if meta.get("year"):
                        years.add(meta["year"])
                    if meta.get("empirical_context"):
                        contexts.add(meta["empirical_context"])
                except Exception:
                    continue
            
            return {
                "paper_types": sorted(list(paper_types)),
                "primary_methods": sorted(list(methods)),
                "journals": sorted(list(journals))[:50],  # Limit for UI
                "year_range": {
                    "min": min(years) if years else None,
                    "max": max(years) if years else None,
                },
                "empirical_contexts": sorted(list(contexts))[:30],
                "chunk_types": VALID_CHUNK_TYPES,
            }
        except Exception as e:
            logger.error(f"Error getting filter options: {e}")
            return {
                "paper_types": ["empirical", "theoretical", "review", "conceptual"],
                "primary_methods": ["qualitative", "quantitative", "case study", "mixed methods"],
                "journals": [],
                "year_range": {"min": 1990, "max": 2026},
                "empirical_contexts": [],
                "chunk_types": VALID_CHUNK_TYPES,
            }
