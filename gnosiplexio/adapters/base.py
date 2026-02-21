"""
Abstract base class for data source adapters.

Adapters provide a unified interface for Gnosiplexio to fetch paper data
from various sources (Veritas Core, Semantic Scholar, BibTeX files, etc.)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class DataSourceAdapter(ABC):
    """
    Abstract base class for data source adapters.
    
    Implementations must provide methods to:
    - Search for papers
    - Get detailed paper profiles
    - Get references (citations) for a paper
    """
    
    @abstractmethod
    async def search_papers(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for papers matching the query.
        
        Args:
            query: Search query string
            limit: Maximum number of results to return
            
        Returns:
            List of paper dictionaries with at least:
            - id: Unique identifier
            - title: Paper title
            - authors: List of author names
            - year: Publication year (optional)
            - abstract: Paper abstract (optional)
        """
        pass
    
    @abstractmethod
    async def get_paper_profile(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed profile for a specific paper.
        
        Args:
            paper_id: Unique paper identifier
            
        Returns:
            Paper profile dictionary with full metadata, or None if not found.
            Should include:
            - id: Unique identifier
            - title: Paper title
            - authors: List of author names
            - year: Publication year
            - abstract: Paper abstract
            - doi: DOI if available
            - citations: Citation count if available
            - references: List of reference IDs if available
        """
        pass
    
    @abstractmethod
    async def get_references(self, paper_id: str) -> List[Dict[str, Any]]:
        """
        Get the references (papers cited by) for a specific paper.
        
        Args:
            paper_id: Unique paper identifier
            
        Returns:
            List of reference dictionaries, each containing at least:
            - id: Reference paper identifier
            - title: Reference paper title
            - authors: List of author names (optional)
            - year: Publication year (optional)
        """
        pass
    
    async def get_citations(self, paper_id: str) -> List[Dict[str, Any]]:
        """
        Get papers that cite the specified paper.
        
        This is optional; default implementation returns empty list.
        
        Args:
            paper_id: Unique paper identifier
            
        Returns:
            List of citing paper dictionaries
        """
        return []
    
    async def health_check(self) -> bool:
        """
        Check if the data source is available.
        
        Returns:
            True if the data source is reachable and functional
        """
        return True
