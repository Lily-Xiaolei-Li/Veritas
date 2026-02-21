# Veritas Core

**Version:** 1.0.0  
**Status:** In Development (95% complete)  
**Developed by Lily Xiaolei Li**

Veritas Core is the foundation platform for academic research assistance.

## Features

- **Library RAG** — Full-text semantic search of academic papers
- **VF Store** — Veritas Fingerprint storage (8 semantic chunks per paper)
- **VF Middleware** — Profile generation from papers
- **Session Manager** — Workspace session management
- **Artifact Manager** — Document and output management
- **AI Chat** — LLM-powered conversation
- **Workbench UI** — Main interface shell
- **Plugin System** — Load add-ons like Scholarly Hollows

## Tech Stack

- **Backend:** FastAPI + Python
- **Frontend:** Next.js + TypeScript
- **Database:** PostgreSQL + Qdrant
- **Embeddings:** bge-m3 (1024d)

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## API

See `docs/api-spec.yaml` for OpenAPI specification.

---

*Part of the Veritas ecosystem*
