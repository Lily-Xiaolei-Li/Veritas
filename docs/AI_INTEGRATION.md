# Veritas - AI Integration Guide

> **For AI Agents**: Claude, GPT, Gemini, etc.
> **Backend**: http://localhost:8001
> **CLI Entry**: `backend/cli/main.py`

---

## Quick Reference

### Environment Setup

```powershell
# Working directory
cd "C:\path\to\Veritas\backend"

# CLI command alias
$CLI = ".\venv\Scripts\python.exe -m cli.main"

# Suppress stderr in JSON mode (recommended)
# All commands: add --json flag, merge streams with 2>&1
```

### Essential Commands

```powershell
# Status check
& $CLI status show --json 2>&1

# List sessions
& $CLI session list --json 2>&1

# Use a session (saves current)
& $CLI session use --session <uuid> --json 2>&1

# List artifacts
& $CLI artifact list --session <uuid> --json 2>&1

# Send chat message
& $CLI chat send --session <uuid> --message "Your message" --json 2>&1
```

---

## JSON Response Contract

### Success Response

```json
{
  "schema_version": "1.0",
  "ok": true,
  "result": "ok",
  "data": { ... },
  "error": null,
  "meta": {}
}
```

### Error Response

```json
{
  "schema_version": "1.0",
  "ok": false,
  "result": null,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": { ... }
  },
  "meta": {}
}
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Business error (CLI_BUSINESS_ERROR) |
| 2 | System error (CLI_SYSTEM_ERROR) |

---

## Session Operations

### Create Session

```powershell
& $CLI session create --name "Research Topic" --json 2>&1
```

Response:
```json
{
  "ok": true,
  "data": {
    "session": {
      "id": "a6444b3c-2a59-4b64-9da6-1450cb804a84",
      "name": "Research Topic",
      "created_at": "2026-02-19T10:30:00Z"
    }
  }
}
```

### List Sessions

```powershell
& $CLI session list --json 2>&1
```

### Set Current Session

```powershell
& $CLI session use --session <uuid> --json 2>&1
```

After this, use `--use-current-session` flag to auto-resolve session.

### Get Current Session

```powershell
& $CLI session current --json 2>&1
```

---

## Artifact Operations

### Create Artifact

```powershell
# From inline text
& $CLI artifact create --session <uuid> --name "notes.md" --type markdown --content "# Notes" --json 2>&1

# From file
& $CLI artifact create --session <uuid> --name "paper.md" --type markdown --file ./paper.md --json 2>&1
```

### List Artifacts

```powershell
& $CLI artifact list --session <uuid> --json 2>&1
```

Response:
```json
{
  "ok": true,
  "data": {
    "artifacts": [
      {
        "id": "12345678-...",
        "filename": "notes.md",
        "artifact_type": "markdown",
        "char_count": 1234,
        "created_at": "2026-02-19T10:30:00Z"
      }
    ]
  }
}
```

### Show Artifact Content

```powershell
& $CLI artifact show --artifact <id> --json 2>&1
```

### Update Artifact

```powershell
& $CLI artifact update --artifact <id> --content "New content" --json 2>&1
# Or from file:
& $CLI artifact update --artifact <id> --file ./updated.md --json 2>&1
```

### Export Artifact

```powershell
& $CLI artifact export --artifact <id> --out ./output.md
```

### Delete Artifact

```powershell
& $CLI artifact delete --artifact <id> --yes --json 2>&1
```

**Note**: `--yes` required for destructive operations.

---

## Library Operations ⭐

### Check Library Status

```powershell
& $CLI library status --json 2>&1
```

Response:
```json
{
  "ok": true,
  "data": {
    "total_papers": 156,
    "in_vf_store": 142,
    "has_chunks_folder": 148,
    "in_excel_index": 150,
    "section_coverage": {
      "abstract": 140,
      "introduction": 156,
      "methodology": 78,
      "conclusion": 150
    },
    "completeness_pct": 91.0
  }
}
```

### Integrity Check

```powershell
& $CLI library check --json 2>&1
```

Response includes:
- `summary`: counts by category
- `priorities`: p1/p2/p3 issue counts
- `priority_1_sample`: sample papers needing attention

### Find Data Gaps

```powershell
# All gaps
& $CLI library gaps --json 2>&1

# Filter by priority
& $CLI library gaps --priority 1 --json 2>&1
```

Priority levels:
| P | Description |
|---|-------------|
| 1 | Has chunks but not in VF Store (easy fix) |
| 2 | No chunks, no VF (needs PDF processing) |
| 3 | In VF Store but no chunks (missing source) |

### Paper Match Check

```powershell
& $CLI library match --paper-id "Hutomo_2020_CarbonAccounting" --json 2>&1
```

Response:
```json
{
  "ok": true,
  "data": {
    "paper": {
      "paper_id": "Hutomo_2020_CarbonAccounting",
      "title": "Carbon Accounting...",
      "doi": "10.1234/..."
    },
    "sqlite_status": {
      "in_vf_store": true,
      "has_chunks_folder": true,
      "sections": {
        "introduction": true,
        "conclusion": true
      }
    },
    "chunks_folder": {
      "match_type": "exact",
      "files_sample": ["introduction.txt", "methodology.txt", ...]
    },
    "qdrant_status": {
      "found": true,
      "pieces": 8
    }
  }
}
```

### VF Store Status

```powershell
& $CLI library vf-status --json 2>&1
```

### Export Library Database

```powershell
# CSV format (Excel compatible)
& $CLI library export --format csv --output library.csv --json 2>&1

# JSON format
& $CLI library export --format json --output library.json --json 2>&1
```

Exported columns: item_id, canonical_id, doi, title, authors, year, journal, paper_type, primary_method, keywords, in_vf_store, in_excel_index, has_chunks, chunk_count, has_abstract, has_introduction, has_methodology, has_conclusion, vf_profile_exists, vf_chunks_count, pdf_filename, chunks_folder, created_at, updated_at

---

## Tools API ⭐

Python tools for extracting paper sections. Import from `backend/tools/`.

### Setup

```python
import sys
sys.path.insert(0, r"C:\path\to\Veritas\backend")

from tools import (
    lookup_introduction,
    lookup_conclusion,
    lookup_references,
    lookup_all_sections,
    AVAILABLE_SECTIONS
)
```

### lookup_introduction(paper_id)

```python
intro = lookup_introduction("Hutomo_2020_CarbonAccounting")
# Returns: str | None
```

### lookup_conclusion(paper_id)

```python
conclusion = lookup_conclusion("Author_2020_Keywords")
# Returns: str | None
```

### lookup_references(paper_id, raw=False)

```python
# As list
refs = lookup_references("paper_id")
# Returns: List[str]
# Example: ["[1] Smith (2015)...", "[2] Brown (2018)..."]

# As raw markdown
refs_md = lookup_references("paper_id", raw=True)
# Returns: str
```

### lookup_all_sections(paper_id)

```python
sections = lookup_all_sections("paper_id")
# Returns: Dict[str, str | None]
# {
#   "abstract": "...",
#   "introduction": "...",
#   "methodology": None,  # if not found
#   "literature_review": "...",
#   "empirical_analysis": "...",
#   "conclusion": "..."
# }
```

### Available Sections

```python
from tools import AVAILABLE_SECTIONS
print(AVAILABLE_SECTIONS)
# ['abstract', 'introduction', 'methodology',
#  'literature_review', 'empirical_analysis', 'conclusion']
```

### Section Success Rates

| Section | Success Rate | Avg Length |
|---------|--------------|------------|
| abstract | 90% | 1,671 chars |
| introduction | 100% | 8,790 chars |
| methodology | 50% | 13,014 chars |
| literature_review | 80% | 13,023 chars |
| empirical_analysis | 100% | 59,417 chars |
| conclusion | 100% | ~1.2-13k chars |

---

## Chat Operations

### Send Message

```powershell
& $CLI chat send --session <uuid> --message "Analyze methodology" --json 2>&1
```

### With Persona

```powershell
& $CLI chat send --session <uuid> --persona drafter --message "Write introduction" --json 2>&1
```

Available personas: `default`, `drafter`, `reviewer`, `referencer`, `templator`, `cleaner`, `thinker`, `skeptic`

### With Artifact Context

```powershell
& $CLI chat send --session <uuid> --artifacts <id1>,<id2> --message "Compare these papers" --json 2>&1
```

### With RAG Search

```powershell
& $CLI chat send --session <uuid> --rag library --rag-top-k 10 --message "Find papers on carbon disclosure" --json 2>&1
```

### Stream Response

```powershell
& $CLI chat send --session <uuid> --message "..." --stream --json 2>&1
```

---

## VF Middleware Operations

### Generate VF Profile

```powershell
& $CLI vf generate --paper-id "Author_2020" --abstract "Paper abstract..." --json 2>&1
```

### Batch Generate

```powershell
& $CLI vf batch --file batch_input.json --json 2>&1
```

### Lookup Profile

```powershell
& $CLI vf lookup --paper-id "Author_2020" --json 2>&1
& $CLI vf lookup --author "Smith" --year 2020 --json 2>&1
```

### VF Stats

```powershell
& $CLI vf stats --json 2>&1
```

### Sync with Library

```powershell
& $CLI vf sync --library-path ./parsed_library --dry-run --json 2>&1
```

---

## Error Handling

### Common Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| `SESSION_NOT_FOUND` | Invalid session UUID | Check session list |
| `ARTIFACT_NOT_FOUND` | Invalid artifact ID | Check artifact list |
| `LIBRARY_DB_NOT_FOUND` | SQLite DB missing | Check data/central_index.sqlite |
| `LIBRARY_PAPER_NOT_FOUND` | Paper ID not in library | Verify paper_id format |
| `CLI_INVALID_ARGUMENTS` | Missing/wrong arguments | Check command syntax |
| `SESSION_REQUIRED_AUTOMATION` | Session not specified | Add --session flag |

### Error Handling Pattern

```python
import json
import subprocess

result = subprocess.run(
    ["python", "-m", "cli.main", "library", "status", "--json"],
    capture_output=True,
    text=True,
    cwd=r"C:\path\to\Veritas\backend"
)

# Parse JSON from stdout (stderr contains logs)
for line in result.stdout.strip().split('\n'):
    try:
        data = json.loads(line)
        if data.get('ok'):
            print("Success:", data['data'])
        else:
            print("Error:", data['error']['code'], data['error']['message'])
        break
    except json.JSONDecodeError:
        continue
```

---

## Best Practices

### 1. Always Use --json Flag

```powershell
# ✅ Correct
& $CLI session list --json 2>&1

# ❌ Wrong (human output, harder to parse)
& $CLI session list
```

### 2. Merge Streams in PowerShell

```powershell
# ✅ Correct
& $CLI command --json 2>&1

# ❌ Wrong (stderr causes PowerShell errors)
& $CLI command --json
```

### 3. Use Full UUIDs

```powershell
# ✅ Correct
--session a6444b3c-2a59-4b64-9da6-1450cb804a84

# ❌ Wrong (short IDs not supported)
--session a6444
```

### 4. Set Current Session for Repeated Operations

```powershell
# Set once
& $CLI session use --session <uuid>

# Then use --use-current-session
& $CLI artifact list --use-current-session --json 2>&1
& $CLI chat send --use-current-session --message "..." --json 2>&1
```

### 5. Use Aliases for Brevity

| Alias | Full |
|-------|------|
| `sess` | `session` |
| `art` | `artifact` |
| `src` | `source` |
| `ls` | `list` |
| `del` | `delete` |

### 6. Paper ID Format

Standard format: `Author_Year_Keywords`

Examples:
- `Hutomo_2020_CarbonAccounting`
- `Smith_2015_VoluntaryDisclosure`
- `Brown_Green_2018_LegitimacyTheory`

### 7. Check Library Before Section Lookup

```python
# First verify paper exists
from tools import lookup_all_sections

sections = lookup_all_sections("paper_id")
if sections is None:
    print("Paper not found in library")
elif all(v is None for v in sections.values()):
    print("Paper found but no sections extracted")
```

---

## Workflow Templates

### Literature Review Extraction

```python
from tools import lookup_introduction, lookup_literature_review, lookup_conclusion

paper_ids = ["Paper1_2020", "Paper2_2021", "Paper3_2022"]

for pid in paper_ids:
    intro = lookup_introduction(pid)
    lit = lookup_literature_review(pid)
    concl = lookup_conclusion(pid)

    print(f"=== {pid} ===")
    if intro:
        print(f"INTRO: {len(intro)} chars")
    if lit:
        print(f"LIT REVIEW: {len(lit)} chars")
    if concl:
        print(f"CONCLUSION: {len(concl)} chars")
```

### Reference Comparison

```python
from tools import lookup_references

all_refs = {}
for pid in paper_ids:
    refs = lookup_references(pid)
    all_refs[pid] = set(refs)

# Find common references
common = set.intersection(*all_refs.values())
print(f"Common references across {len(paper_ids)} papers: {len(common)}")
```

### Batch Library Check

```powershell
$papers = @("Paper1_2020", "Paper2_2021", "Paper3_2022")
foreach ($p in $papers) {
    & $CLI library match --paper-id $p --json 2>&1 | ConvertFrom-Json
}
```

---

## REST API Fallback

When CLI has limitations, use REST API directly:

```powershell
$BASE = "http://localhost:8001/api/v1"

# Health check
curl.exe -s "$BASE/health"

# List sessions
curl.exe -s "$BASE/sessions"

# Get artifact content
curl.exe -s "$BASE/artifacts/<id>/content"

# Create artifact
curl.exe -s -X POST "$BASE/sessions/<uuid>/artifacts" `
  -H "Content-Type: application/json" `
  -d '{"filename":"notes.md","content":"# Notes","artifact_type":"file"}'
```

---

## Version Info

- CLI Version: 1.0
- API Version: 1.0
- Backend Port: 8001
- Qdrant Port: 6333
- PostgreSQL Port: 5433

---

*Last updated: 2026-02-19*
