# Scholarly Hollows (SH)

**Academic magic spells for Veritas** — advanced AI-powered research tools

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/your-repo)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📖 Description

Scholarly Hollows (SH) is a Veritas plugin that provides powerful "magic spells" for academic research. Each spell is an AI-enhanced tool designed to assist researchers with citation management, verification, and literature discovery.

---

## 🪄 Spells

| Spell | Chinese Name | Description |
|-------|--------------|-------------|
| **Veritafactum** | 真知照见 | Sentence-by-sentence citation verification — checks if claims are properly supported by cited sources |
| **Citalio** | 引经据典 | Automatic citation recommendation — finds relevant papers to cite for uncited claims |
| **Proliferomaxima** | 寻书万卷 | Citation network proliferation — expands your bibliography by exploring references and citations |
| **Ex-portario** | 破壁取珠 | Paywall bypass for full-text download — retrieves PDFs through legitimate channels |

---

## 📦 Installation

Scholarly Hollows is designed as a plugin for **Veritas Core**. 

### As a Veritas Plugin

1. Ensure Veritas Core is installed and running
2. Copy the `scholarly-hollows/` directory to `veritas/plugins/`
3. Veritas will auto-discover and load the plugin on startup

```
veritas/
├── plugins/
│   └── scholarly-hollows/    ← Place here
│       ├── manifest.json
│       ├── routes/
│       ├── services/
│       └── frontend/
```

### Dependencies

Install Python dependencies:

```bash
pip install -r scholarly-hollows/requirements.txt
```

---

## 🚀 Usage

Once loaded, Scholarly Hollows exposes its API under `/api/v1/sh/`:

### Health Check

```http
GET /api/v1/sh/health
```

Returns plugin status and available spells.

### Veritafactum (Citation Verification)

```http
POST /api/v1/sh/veritafactum/check
Content-Type: application/json

{
  "document_id": "doc_123",
  "mode": "full"  // or "selection"
}
```

### Citalio (Citation Recommendation)

```http
POST /api/v1/sh/citalio/recommend
Content-Type: application/json

{
  "sentence": "Deep learning has revolutionized NLP.",
  "context": "...",
  "top_k": 5
}
```

### Proliferomaxima (Citation Network Expansion)

```http
POST /api/v1/sh/proliferomaxima/expand
Content-Type: application/json

{
  "paper_ids": ["doi:10.1234/example"],
  "depth": 2,
  "max_papers": 50
}
```

---

## 🏗️ Architecture

```
scholarly-hollows/
├── manifest.json          # Plugin metadata
├── requirements.txt       # Python dependencies
├── routes/                # FastAPI route handlers
│   ├── __init__.py        # Combined router (exported)
│   ├── veritafactum.py
│   ├── citalio.py
│   └── proliferomaxima.py
├── services/              # Business logic
│   ├── veritafactum/      # Verification engine
│   ├── citalio/           # Recommendation engine
│   └── proliferomaxima/   # Network expansion engine
└── frontend/              # React components
    ├── veritafactum/
    ├── citalio/
    └── proliferomaxima/
```

---

## 👩‍💻 Author

**Lily Xiaolei Li**

---

## 📄 License

MIT License — see [LICENSE](../LICENSE) for details.
