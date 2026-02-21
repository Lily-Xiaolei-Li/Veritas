# Agent-B Research CLI Reference

**Version:** 1.0.0 | **Updated:** 2026-02-19

Complete reference for the `abr` / `cli.main` command-line interface.

---

## Table of Contents

1. [General Usage](#general-usage)
2. [Global Flags](#global-flags)
3. [Session Commands](#session-commands)
4. [Artifact Commands](#artifact-commands)
5. [Chat Commands](#chat-commands)
6. [Source Commands](#source-commands)
7. [Persona Commands](#persona-commands)
8. [Library Commands](#library-commands)
9. [VF Commands](#vf-commands)
10. [Run Commands](#run-commands)
11. [Context Commands](#context-commands)
12. [Status Commands](#status-commands)
13. [Checker Commands](#checker-commands)
14. [Log Commands](#log-commands)
15. [Aliases](#aliases)
16. [Exit Codes](#exit-codes)
17. [Error Codes](#error-codes)

---

## General Usage

```
python -m cli.main <resource> <action> [options]
```

**From backend directory:**
```powershell
cd "C:\Users\Barry Li (UoN)\clawd\projects\Agent-B-Research\backend"
.\venv\Scripts\python.exe -m cli.main <resource> <action> [options]
```

**PowerShell alias:**
```powershell
$CLI = ".\venv\Scripts\python.exe -m cli.main"
& $CLI <resource> <action> [options]
```

---

## Global Flags

These flags work with any command:

| Flag | Description |
|------|-------------|
| `--json` | Output machine-readable JSON |
| `--quiet` | Suppress non-essential output |
| `--yes` | Auto-confirm destructive operations |
| `--use-current-session` | Use saved current session |
| `--automation` | Force automation mode |
| `--interactive` | Force interactive mode |
| `--api-version <v>` | CLI/API contract version (default: 1) |
| `--log-format <fmt>` | Log format: `text` or `jsonl` |
| `--log-file <path>` | Optional log file path |

---

## Session Commands

Manage research workspaces.

### session create

Create a new session.

```
session create --name <name> [--idempotency-key <key>] [--dedupe-name]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--name` | Yes | Session name |
| `--idempotency-key` | No | Prevent duplicate creation |
| `--dedupe-name` | No | Use name as idempotency key |

**Example:**
```powershell
& $CLI session create --name "Chapter 3 Draft" --json
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "session": {
      "id": "uuid-here",
      "name": "Chapter 3 Draft",
      "created_at": "2026-02-19T10:00:00Z"
    }
  }
}
```

---

### session list

List all sessions.

```
session list
```

**Example:**
```powershell
& $CLI session list --json
```

---

### session show

Show session details.

```
session show --session <uuid>
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--session` | Yes | Session UUID |

---

### session use

Set current session (saved for subsequent commands).

```
session use --session <uuid>
```

---

### session current

Show current session.

```
session current
```

---

## Artifact Commands

Manage documents within sessions.

### artifact create

Create a new artifact.

```
artifact create --session <uuid> --name <name> [--type <type>] [--content <text> | --file <path>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--session` | Yes | Session UUID |
| `--name` | Yes | Artifact filename |
| `--type` | No | Type: `markdown` (default), `text`, `json` |
| `--content` | No* | Inline content |
| `--file` | No* | File path for content |
| `--provenance-type` | No | `manual`, `imported`, `run` |
| `--run` | No | Run ID (for provenance type `run`) |

*Either `--content` or `--file` required.

**Example:**
```powershell
& $CLI artifact create --session $sid --name "outline.md" --type markdown --content "# Outline" --json
```

---

### artifact list

List artifacts in a session.

```
artifact list --session <uuid>
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "artifacts": [
      {
        "id": "artifact-uuid",
        "filename": "outline.md",
        "artifact_type": "markdown",
        "char_count": 123,
        "created_at": "..."
      }
    ]
  }
}
```

---

### artifact show

Show artifact details and content.

```
artifact show --artifact <id>
```

---

### artifact export

Export artifact content to file.

```
artifact export --artifact <id> --out <path>
```

---

### artifact update

Update artifact content.

```
artifact update --artifact <id> [--content <text> | --file <path>]
```

---

### artifact delete

Delete an artifact.

```
artifact delete --artifact <id> --yes
```

**Warning:** `--yes` required. Deletion is permanent.

---

### artifact rename

Rename an artifact.

```
artifact rename --artifact <id> --name <new-name>
```

---

### artifact copy

Copy an artifact (creates duplicate).

```
artifact copy --artifact <id>
```

---

### artifact preview

Get artifact preview (truncated content).

```
artifact preview --artifact <id>
```

---

### artifact draft

Manage artifact drafts.

```
# Show draft
artifact draft --artifact <id>

# Save draft
artifact draft --artifact <id> --save [--content <text> | --file <path>]

# Clear draft
artifact draft --artifact <id> --save --clear
```

---

## Chat Commands

AI conversation and history.

### chat send

Send a message to AI.

```
chat send --session <uuid> --message <text> [options]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--session` | Yes | Session UUID |
| `--message` | Yes | Message content |
| `--persona` | No | Persona ID (drafter, reviewer, etc.) |
| `--artifacts` | No | Comma-separated artifact IDs for context |
| `--rag` | No | Comma-separated RAG sources (e.g., `library`) |
| `--rag-top-k` | No | Number of RAG results (default: 5) |
| `--stream` | No | Stream token output |

**Example with RAG:**
```powershell
& $CLI chat send --session $sid --persona drafter --artifacts "id1,id2" --rag library --rag-top-k 10 --message "Write introduction" --json
```

---

### chat history

Get chat history for a session.

```
chat history --session <uuid>
```

---

## Source Commands

Manage research materials and imports.

### source add

Add a source to session.

```
source add --session <uuid> [--file <path> | --url <url> | --text <content>]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--session` | Yes | Session UUID |
| `--file` | No* | File path (PDF, DOCX, TXT, MD) |
| `--url` | No* | Web URL to fetch |
| `--text` | No* | Inline text content |
| `--idempotency-key` | No | Prevent duplicate creation |
| `--dedupe` | No | Dedupe by content hash |

*One of `--file`, `--url`, or `--text` required.

---

### source list

List sources in session.

```
source list [--session <uuid>]
```

---

### source show

Show source details.

```
source show --source <id>
```

---

### source remove

Remove a source.

```
source remove --source <id>
```

---

### source tag

Tag a source.

```
source tag --source <id> --tag <tag>
```

---

### source search

Search sources by query.

```
source search <query>
```

---

### source download

Download a paper by DOI/title/URL.

```
source download [--doi <doi> | --title <title> | --url <url>]
```

---

### source upload

Upload PDF file(s) to library.

```
source upload <path>
```

Path can be a single file or folder.

---

### source batch

Batch import from file.

```
source batch [--csv <path> | --dois <path> | --bibtex <path>]
```

---

### source queue

Show download queue status.

```
source queue
```

---

### source stats

Show source statistics.

```
source stats
```

---

### source proxy-download

Queue DOIs for proxy download.

```
source proxy-download [--doi <doi>] [--doi-list <path>] [--out <path>]
```

| Parameter | Description |
|-----------|-------------|
| `--doi` | Single DOI (repeatable) |
| `--doi-list` | Text file with DOI list |
| `--out` | Output queue JSON path |

---

## Persona Commands

Manage AI personas/roles.

### persona list

List all personas.

```
persona list
```

**Built-in personas:**

| ID | Name | Purpose |
|----|------|---------|
| `default` | Default Assistant | General academic help |
| `drafter` | The Drafter | Journal-quality writing |
| `reviewer` | The Reviewer | Simulate peer reviewer |
| `referencer` | The Referencer | Citation checking |
| `templator` | The Templator | Extract templates from papers |
| `cleaner` | The Cleaner | Fix formatting issues |
| `thinker` | The Thinker | Find patterns and insights |
| `skeptic` | The Skeptic | Devil's advocate |

---

### persona create

Create custom persona.

```
persona create --name <name> --system-prompt <prompt>
```

---

### persona show

Show persona details.

```
persona show --persona <id>
```

---

### persona update

Update persona.

```
persona update --persona <id> [--name <name>] [--system-prompt <prompt>]
```

---

### persona version

Show/bump persona version.

```
persona version --persona <id> [--bump]
```

---

### persona select

Select persona for session.

```
persona select --persona <id> --session <uuid>
```

---

### persona export

Export persona to file.

```
persona export --persona <id> --out <path>
```

---

### persona import

Import persona from file.

```
persona import --file <path>
```

---

## Library Commands

Manage and diagnose the research paper library.

### library status

Library status overview.

```
library status
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "total_papers": 156,
    "in_vf_store": 142,
    "has_chunks_folder": 148,
    "in_excel_index": 150,
    "has_canonical_id": 145,
    "duplicate_paper_ids": 0,
    "section_coverage": {
      "abstract": 140,
      "introduction": 156,
      "methodology": 78,
      "conclusion": 150
    },
    "chunk_stats": {
      "min": 3,
      "max": 45,
      "avg": 12.5
    },
    "completeness_pct": 91.0
  }
}
```

---

### library check

Full integrity check.

```
library check
```

Cross-checks SQLite database with Qdrant VF Store and chunks folders.

**Response includes:**
- `summary`: Category counts
- `priorities`: P1/P2/P3 issue counts
- `priority_1_sample`: Papers needing immediate attention
- `priority_2_sample`: Papers needing PDF processing

---

### library gaps

Data gap analysis.

```
library gaps [--priority <1|2|3>]
```

| Priority | Description |
|----------|-------------|
| 1 | Has chunks but not in VF Store (easy fix) |
| 2 | No chunks, no VF Store (needs PDF) |
| 3 | In VF Store but no chunks (missing source) |

---

### library match

Check how a paper matches across systems.

```
library match --paper-id <paper_id>
```

**Response:**
```json
{
  "ok": true,
  "data": {
    "paper": {
      "paper_id": "Hutomo_2020_CarbonAccounting",
      "title": "...",
      "doi": "10.1234/...",
      "year": 2020
    },
    "sqlite_status": {
      "in_vf_store": true,
      "has_chunks_folder": true,
      "chunk_count": 12,
      "sections": {
        "abstract": true,
        "introduction": true,
        "methodology": false,
        "conclusion": true
      }
    },
    "chunks_folder": {
      "match_type": "exact",
      "path": "C:/path/to/chunks",
      "files_sample": ["introduction.txt", "conclusion.txt"]
    },
    "qdrant_status": {
      "found": true,
      "pieces": 8,
      "chunk_ids": ["piece1", "piece2", ...]
    }
  }
}
```

---

### library vf-status

VF Store status and 8-piece structure analysis.

```
library vf-status
```

---

### library fix

Generate fix plan for library issues.

```
library fix --priority <1|2|3> [--dry-run]
```

| Parameter | Description |
|-----------|-------------|
| `--priority` | Which priority level to fix |
| `--dry-run` | Show plan without executing |

---

### library export

Export library database to file.

```
library export [--format <csv|json>] [--output <path>] [--include-paths]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--format` | csv | Output format |
| `--output` | auto | Output file path |
| `--include-paths` | false | Include file path columns |

**CSV columns:** item_id, canonical_id, doi, title, authors, year, journal, paper_type, primary_method, keywords, in_vf_store, in_excel_index, has_chunks, chunk_count, has_abstract, has_introduction, has_methodology, has_conclusion, vf_profile_exists, vf_chunks_count, pdf_filename, chunks_folder, created_at, updated_at

---

## VF Commands

Manage Vector Fingerprint profiles.

### vf generate

Generate VF profile for a paper.

```
vf generate --paper-id <id> [options]
```

| Parameter | Description |
|-----------|-------------|
| `--paper-id` | Canonical paper ID (e.g., `Author_2020`) |
| `--metadata-json` | Metadata JSON string |
| `--abstract` | Abstract text |
| `--abstract-file` | Path to abstract file |
| `--full-text` | Full text content |
| `--full-text-file` | Path to full text file |
| `--external` | Mark as external (in_library=false) |
| `--agent` | Agent: `helper`, `dr-xiaolei`, `asst-xiaolei` |

---

### vf batch

Batch generate VF profiles.

```
vf batch --file <path>
```

Input file format:
```json
{
  "items": [
    {"paper_id": "...", "abstract": "..."},
    {"paper_id": "...", "abstract": "..."}
  ]
}
```

---

### vf lookup

Lookup VF profile.

```
vf lookup [--paper-id <id> | --author <surname> --year <year>]
```

---

### vf stats

VF Store statistics.

```
vf stats
```

---

### vf list

List VF profiles.

```
vf list [--limit <n>] [--offset <n>]
```

---

### vf delete

Delete VF profile.

```
vf delete --paper-id <id>
```

---

### vf sync

Sync VF Store with parsed library.

```
vf sync [--library-path <path>] [--agent <name>] [--dry-run] [--concurrency <n>]
```

---

## Run Commands

Manage AI runs (execution traces).

### run list

List runs.

```
run list [--session <uuid>]
```

---

### run show

Show run details.

```
run show --run <id>
```

---

### run cancel

Cancel a running run.

```
run cancel --run <id>
```

---

### run retry

Retry a failed run.

```
run retry --run <id>
```

---

### run resume

Resume a paused run.

```
run resume --run <id>
```

---

## Context Commands

Manage context at different scopes.

### context set

Set context content.

```
context set --scope <global|session|run> --content <text> [--session <uuid>] [--run <id>]
```

---

### context get

Get context content.

```
context get --scope <global|session|run> [--session <uuid>] [--run <id>]
```

---

### context clear

Clear context.

```
context clear --scope <global|session|run> [--session <uuid>] [--run <id>]
```

---

### context resolve

Resolve effective context (merges all scopes).

```
context resolve [--session <uuid>] [--run <id>]
```

---

## Status Commands

System health and diagnostics.

### status show

Show system status.

```
status show
```

---

### status doctor

Run diagnostic checks.

```
status doctor
```

---

## Checker Commands

Academic writing quality checker.

### checker run

Run quality check on artifact.

```
checker run --session <uuid> --artifact <id> [--no-citations] [--no-ai] [--no-flow]
```

| Flag | Description |
|------|-------------|
| `--no-citations` | Skip citation checking |
| `--no-ai` | Skip AI pattern detection |
| `--no-flow` | Skip flow analysis |

---

### checker status

Check run status.

```
checker status <run_id>
```

---

### checker results

Get checker results.

```
checker results <run_id>
```

---

## Log Commands

View application logs.

### log stream

Stream logs in real-time.

```
log stream [--level <DEBUG|INFO|WARNING|ERROR>] [--no-color]
```

---

### log recent

Get recent log entries.

```
log recent [--limit <n>] [--level <level>]
```

---

## Aliases

Short forms for common operations:

| Alias | Full Command |
|-------|--------------|
| `sess` | `session` |
| `art` | `artifact` |
| `src` | `source` |
| `ctx` | `context` |
| `pers` | `persona` |
| `rn` | `run` |
| `stat` | `status` |
| `ls` | `list` |
| `cur` | `current` |
| `del` | `delete` |
| `rm` | `remove` (source) / `delete` (artifact) |

**Example:**
```powershell
& $CLI sess ls --json    # session list
& $CLI art ls --session $sid --json    # artifact list
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Business error (invalid input, not found, etc.) |
| `2` | System error (crash, unhandled exception) |

---

## Error Codes

### Session Errors
| Code | Description |
|------|-------------|
| `SESSION_NOT_FOUND` | Session UUID does not exist |
| `SESSION_REQUIRED_AUTOMATION` | --session required in automation mode |
| `SESSION_CURRENT_NOT_SET` | No current session saved |

### Artifact Errors
| Code | Description |
|------|-------------|
| `ARTIFACT_NOT_FOUND` | Artifact ID does not exist |
| `ARTIFACT_CONTENT_MISSING` | Neither --content nor --file provided |

### Library Errors
| Code | Description |
|------|-------------|
| `LIBRARY_DB_NOT_FOUND` | central_index.sqlite missing |
| `LIBRARY_PAPER_NOT_FOUND` | Paper ID not in database |
| `LIBRARY_STATUS_ERROR` | Failed to get status |
| `LIBRARY_CHECK_ERROR` | Integrity check failed |
| `LIBRARY_GAPS_ERROR` | Gap analysis failed |
| `LIBRARY_MATCH_ERROR` | Match check failed |
| `LIBRARY_FIX_INVALID_PRIORITY` | --priority must be 1, 2, or 3 |
| `LIBRARY_EXPORT_ERROR` | Export failed |

### VF Errors
| Code | Description |
|------|-------------|
| `VF_PAPER_ID_REQUIRED` | --paper-id is required |
| `VF_GENERATION_FAILED` | Profile generation failed |

### CLI Errors
| Code | Description |
|------|-------------|
| `CLI_INVALID_ARGUMENTS` | Invalid command arguments |
| `CLI_MODE_CONFLICT` | --automation and --interactive together |
| `CLI_API_VERSION_UNSUPPORTED` | Unsupported API version |
| `CLI_UNHANDLED_EXCEPTION` | Unexpected system error |

---

## JSON Output Examples

### Success
```json
{
  "schema_version": "1.0",
  "ok": true,
  "result": "ok",
  "data": {
    "sessions": [...]
  },
  "error": null,
  "meta": {}
}
```

### Error
```json
{
  "schema_version": "1.0",
  "ok": false,
  "result": null,
  "data": null,
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "Session not found",
    "details": {
      "session": "invalid-uuid"
    }
  },
  "meta": {}
}
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENTB_API_URL` | `http://localhost:8001/api/v1` | Backend API URL |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |

### Configuration Files

| File | Purpose |
|------|---------|
| `backend/.env` | Environment variables |
| `backend/data/cli_state.json` | Current session state |
| `backend/data/central_index.sqlite` | Library index database |

---

*Agent-B Research CLI Reference v1.0.0*
