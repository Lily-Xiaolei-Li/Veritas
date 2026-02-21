# Gnosiplexio (GP)

**中文名:** 织智成网  
**Version:** 0.1.0  
**Status:** Design Phase (0% complete)

Gnosiplexio is an independent knowledge graph software for academic research.

## Vision

Build and visualize knowledge graphs from academic literature:
- Paper relationships and citation networks
- Concept and theory connections
- Author collaboration networks
- Research trend analysis

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

## Tech Stack (Planned)

- **Graph Store:** Neo4j or NetworkX
- **Visualization:** D3.js or Cytoscape
- **Query Engine:** Cypher
- **Backend:** FastAPI
- **Frontend:** React

## Data Source Adapters

```python
class DataSourceAdapter(ABC):
    async def search_papers(query, limit) -> List[Paper]
    async def get_paper_profile(paper_id) -> Optional[VFProfile]
    async def get_references(paper_id) -> List[Reference]
```

Implementations:
- `VeritasAdapter` — Connect to Veritas Core API
- `SemanticScholarAdapter` — Semantic Scholar API
- `BibTeXAdapter` — Local BibTeX files

---

*Part of the Veritas ecosystem (optional)*
