"""
Veritas Adapter — Connect Gnosiplexio to Veritas Core API.

This adapter allows Gnosiplexio to use Veritas Core as a data source,
fetching paper profiles, search results, and references via the API.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

from .base import DataSourceAdapter


class VeritasAdapter(DataSourceAdapter):
    """
    Data source adapter that connects to Veritas Core API.
    
    Veritas Core provides:
    - Paper search via /api/v1/search
    - VF (Veritas Fingerprint) profiles via /api/v1/profile/{paper_id}
    - Reference data via /api/v1/references/{paper_id}
    
    Configuration:
        VERITAS_CORE_URL: Base URL for Veritas Core (default: http://localhost:8001)
        VERITAS_CORE_TIMEOUT: Request timeout in seconds (default: 30)
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the Veritas adapter.
        
        Args:
            base_url: Veritas Core API base URL (defaults to VERITAS_CORE_URL env var)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or os.getenv("VERITAS_CORE_URL", "http://localhost:8001")
        self.base_url = self.base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"Accept": "application/json"},
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def search_papers(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for papers using Veritas Core search endpoint.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of paper dictionaries
        """
        client = await self._get_client()
        
        try:
            response = await client.get(
                "/api/v1/search",
                params={"q": query, "limit": limit},
            )
            response.raise_for_status()
            data = response.json()
            
            # Normalize response format
            results = data.get("results", data.get("papers", []))
            return [self._normalize_paper(p) for p in results]
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise
        except httpx.RequestError:
            return []
    
    async def get_paper_profile(self, paper_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed paper profile (VF) from Veritas Core.
        
        Args:
            paper_id: Paper identifier (DOI, work_id, or internal ID)
            
        Returns:
            Paper profile dictionary or None if not found
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"/api/v1/profile/{paper_id}")
            response.raise_for_status()
            data = response.json()
            return self._normalize_paper(data)
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except httpx.RequestError:
            return None
    
    async def get_references(self, paper_id: str) -> List[Dict[str, Any]]:
        """
        Get references for a paper from Veritas Core.
        
        Args:
            paper_id: Paper identifier
            
        Returns:
            List of reference paper dictionaries
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"/api/v1/references/{paper_id}")
            response.raise_for_status()
            data = response.json()
            
            refs = data.get("references", data if isinstance(data, list) else [])
            return [self._normalize_paper(r) for r in refs]
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise
        except httpx.RequestError:
            return []
    
    async def get_citations(self, paper_id: str) -> List[Dict[str, Any]]:
        """
        Get papers that cite the specified paper.
        
        Args:
            paper_id: Paper identifier
            
        Returns:
            List of citing paper dictionaries
        """
        client = await self._get_client()
        
        try:
            response = await client.get(f"/api/v1/citations/{paper_id}")
            response.raise_for_status()
            data = response.json()
            
            citations = data.get("citations", data if isinstance(data, list) else [])
            return [self._normalize_paper(c) for c in citations]
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise
        except httpx.RequestError:
            return []
    
    async def health_check(self) -> bool:
        """Check if Veritas Core is reachable."""
        client = await self._get_client()
        
        try:
            response = await client.get("/api/v1/health")
            return response.status_code == 200
        except httpx.RequestError:
            return False
    
    def _normalize_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize paper data to a consistent format.
        
        Handles different field names from various Veritas endpoints.
        """
        # Extract ID (could be id, work_id, paper_id, doi)
        paper_id = (
            paper.get("id") or 
            paper.get("work_id") or 
            paper.get("paper_id") or 
            paper.get("doi") or 
            ""
        )
        
        # Extract authors (could be list of strings or dicts)
        raw_authors = paper.get("authors", [])
        if raw_authors and isinstance(raw_authors[0], dict):
            authors = [a.get("name", a.get("display_name", "")) for a in raw_authors]
        else:
            authors = raw_authors
        
        # Extract year (could be year, publication_year, pub_year)
        year = (
            paper.get("year") or 
            paper.get("publication_year") or 
            paper.get("pub_year")
        )
        
        return {
            "id": paper_id,
            "title": paper.get("title", ""),
            "authors": authors,
            "year": year,
            "abstract": paper.get("abstract", ""),
            "doi": paper.get("doi", ""),
            "citations": paper.get("citations", paper.get("citation_count", 0)),
            "source": "veritas",
            # Preserve any additional fields
            **{k: v for k, v in paper.items() if k not in (
                "id", "work_id", "paper_id", "title", "authors", 
                "year", "publication_year", "pub_year", "abstract", 
                "doi", "citations", "citation_count"
            )},
        }
    
    def __repr__(self) -> str:
        return f"VeritasAdapter(base_url={self.base_url!r})"
