"""
Gnosiplexio Data Source Adapters.

Adapters provide a unified interface for fetching paper data from various sources.

Available adapters:
- DataSourceAdapter: Abstract base class (async)
- VeritasAdapter: Connect to Veritas Core API (async)
- GenericAdapter: Read from JSON/CSV files (sync)
"""
from .base import DataSourceAdapter
from .veritas_adapter import VeritasAdapter
from .generic_adapter import GenericAdapter
from .types import Citation, SearchResult, WorkRecord

__all__ = [
    "DataSourceAdapter",
    "VeritasAdapter",
    "GenericAdapter",
    "Citation",
    "SearchResult",
    "WorkRecord",
]
