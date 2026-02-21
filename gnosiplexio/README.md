# Gnosiplexio (GP)

**中文名:** 织智成网  
**Version:** 0.1.0  
**Status:** Phase 4.1 - Independent Structure Complete

Gnosiplexio is an independent knowledge graph software for academic research.

## Vision

Build and visualize knowledge graphs from academic literature:
- Paper relationships and citation networks
- Concept and theory connections
- Author collaboration networks
- Research trend analysis

## Directory Structure

```
gnosiplexio/
├── adapters/           # Data source adapters
│   ├── __init__.py
│   ├── base.py         # Abstract DataSourceAdapter
│   └── veritas_adapter.py  # Veritas Core API adapter
├── api/                # FastAPI routes
│   ├── __init__.py
│   └── routes.py       # API endpoints
├── core/               # Core engine components
│   ├── __init__.py
│   ├── engine.py       # Main GnosiplexioEngine
│   ├── graph_store.py  # Graph storage
│   ├── network_enricher.py
│   ├── credibility_scorer.py
│   ├── position_calculator.py
│   ├── concept_drift.py
│   ├── self_growth.py
│   └── scheduler.py
├── docs/               # Documentation
├── frontend/           # Web UI (planned)
├── requirements.txt
└── README.md
```

## Running Modes

### 1. Standalone Mode
Run independently with external data sources:
- Semantic Scholar API
- Local BibTeX files
- Custom adapters

### 2. Veritas Add-On Mode
Connect to Veritas Core for rich data:
- Read from VF Store (Veritas Fingerprints)
- Search Library RAG
- Leverage existing paper profiles

## Installation

```bash
pip install -r requirements.txt
```

## Data Source Adapters

Adapters provide a unified interface for fetching paper data from various sources.

### Abstract Base Class

```python
from gnosiplexio.adapters import DataSourceAdapter

class DataSourceAdapter(ABC):
    """Abstract base class for data source adapters."""
    
    async def search_papers(query: str, limit: int = 20) -> List[dict]
        """Search for papers matching the query."""
    
    async def get_paper_profile(paper_id: str) -> Optional[dict]
        """Get detailed profile for a specific paper."""
    
    async def get_references(paper_id: str) -> List[dict]
        """Get references (papers cited by) for a paper."""
    
    async def get_citations(paper_id: str) -> List[dict]
        """Get papers that cite the specified paper (optional)."""
    
    async def health_check() -> bool
        """Check if the data source is available."""
```

### Veritas Adapter

Connects Gnosiplexio to Veritas Core API:

```python
from gnosiplexio.adapters import VeritasAdapter

# Initialize with default URL (localhost:8001)
adapter = VeritasAdapter()

# Or specify custom URL
adapter = VeritasAdapter(base_url="http://veritas-core:8001")

# Use the adapter
papers = await adapter.search_papers("machine learning", limit=10)
profile = await adapter.get_paper_profile("10.1234/example.doi")
refs = await adapter.get_references("10.1234/example.doi")

# Clean up
await adapter.close()
```

**Configuration via Environment Variables:**
- `VERITAS_CORE_URL`: Base URL for Veritas Core (default: `http://localhost:8001`)
- `VERITAS_CORE_TIMEOUT`: Request timeout in seconds (default: `30`)

### Implementing Custom Adapters

To add a new data source, implement the `DataSourceAdapter` interface:

```python
from gnosiplexio.adapters import DataSourceAdapter

class MyCustomAdapter(DataSourceAdapter):
    async def search_papers(self, query: str, limit: int = 20) -> List[dict]:
        # Your implementation
        pass
    
    async def get_paper_profile(self, paper_id: str) -> Optional[dict]:
        # Your implementation
        pass
    
    async def get_references(self, paper_id: str) -> List[dict]:
        # Your implementation
        pass
```

## Tech Stack

- **Graph Store:** NetworkX (dev) / Neo4j (production)
- **Visualization:** D3.js or Cytoscape (planned)
- **Query Engine:** Cypher (Neo4j) or NetworkX queries
- **Backend:** FastAPI
- **Frontend:** React (planned)
- **HTTP Client:** httpx

## API Endpoints

When running in standalone mode:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/gnosiplexio/ingest` | POST | Ingest a paper |
| `/api/v1/gnosiplexio/ingest-all` | POST | Ingest all papers from adapter |
| `/api/v1/gnosiplexio/node/{id}` | GET | Get node with network knowledge |
| `/api/v1/gnosiplexio/neighborhood/{id}` | GET | Get ego network |
| `/api/v1/gnosiplexio/search` | GET | Search the graph |
| `/api/v1/gnosiplexio/credibility/{id}` | GET | Get credibility report |
| `/api/v1/gnosiplexio/graph` | GET | Export full graph |
| `/api/v1/gnosiplexio/stats` | GET | Get network statistics |
| `/api/v1/gnosiplexio/compare` | POST | Compare two nodes |

---

*Part of the Veritas ecosystem (optional integration)*
