# Agent-B-Research — AI CLI Guide

> For AI agents interacting with Agent-B-Research programmatically.  
> Backend runs on **port 8001**. CLI outputs JSON to stdout when `--json` is passed.

## Quick Start

```powershell
# All commands run from the backend directory
cd "C:\Users\Barry Li (UoN)\clawd\projects\Agent-B-Research\backend"
$CLI = ".\venv\Scripts\python.exe -m cli.main"

# List sessions
& $CLI session list --json 2>&1

# List artifacts for a session
& $CLI artifact list --session <session-uuid> --json 2>&1

# List runs for a session
& $CLI run list --session <session-uuid> --json 2>&1
```

**PowerShell note:** stderr contains log lines that PowerShell renders as errors. Use `2>&1` to merge streams, then parse the JSON line from stdout.

## CLI Command Reference

### Sessions
```powershell
# List all sessions
& $CLI session list --json

# Create a new session
& $CLI session create --name "My Research" --json

# Show session details
& $CLI session show --session <uuid> --json

# Set current session (for commands that auto-resolve session)
& $CLI session use --session <uuid>

# Show current session
& $CLI session current --json
```

### Artifacts
```powershell
# List artifacts in a session
& $CLI artifact list --session <uuid> --json

# Create artifact from text
& $CLI artifact create --session <uuid> --name "notes.md" --type markdown --content "# Notes" --json

# Create artifact from file
& $CLI artifact create --session <uuid> --name "paper.md" --type markdown --file ./paper.md --json

# Show artifact details
& $CLI artifact show --artifact <artifact-id> --json

# Export artifact to file
& $CLI artifact export --artifact <artifact-id> --out ./output.md

# Delete artifact (requires --yes)
& $CLI artifact delete --artifact <artifact-id> --yes --json
```

### Runs
```powershell
# List runs (optionally filtered by session)
& $CLI run list --session <uuid> --json

# Show run details
& $CLI run show --run <run-id> --json

# Cancel a running run
& $CLI run cancel --run <run-id> --json
```

### Chat
```powershell
# Send a message (uses XiaoLei Gateway for AI response)
& $CLI chat send --session <uuid> --message "Analyze this paper" --json

# Stream response tokens
& $CLI chat send --session <uuid> --message "Summarize" --stream --json

# View chat history (fetches from backend API)
& $CLI chat history --session <uuid> --json
```

### Personas
```powershell
# List personas
& $CLI persona list --json

# Create a persona
& $CLI persona create --name "Academic Reviewer" --system-prompt "You are a critical academic reviewer..." --json

# Select persona for a session
& $CLI persona select --persona <id> --session <uuid> --json
```

### Sources
```powershell
# Add a file source
& $CLI source add --session <uuid> --file ./paper.pdf --json

# Add a URL source
& $CLI source add --session <uuid> --url "https://example.com/paper" --json

# List sources
& $CLI source list --session <uuid> --json
```

### Context
```powershell
# Set global context
& $CLI context set --scope global --content "Focus on methodology" --json

# Set session context
& $CLI context set --scope session --session <uuid> --content "Paper 2 analysis" --json

# Resolve effective context (merges global + session + run)
& $CLI context resolve --session <uuid> --json
```

### Status & Logs
```powershell
& $CLI status show --json
& $CLI status doctor --json
& $CLI log recent --limit 50 --json
```

## REST API Fallback

When the CLI has limitations, use the REST API directly:

```powershell
$BASE = "http://localhost:8001/api/v1"

# List sessions
curl.exe -s "$BASE/sessions"

# List artifacts for session
curl.exe -s "$BASE/sessions/<uuid>/artifacts"

# Get artifact content
curl.exe -s "$BASE/artifacts/<artifact-id>/content"

# List runs for session
curl.exe -s "$BASE/sessions/<uuid>/runs"

# Get artifact preview
curl.exe -s "$BASE/artifacts/<artifact-id>/preview"

# Create artifact (POST)
curl.exe -s -X POST "$BASE/sessions/<uuid>/artifacts" -H "Content-Type: application/json" -d '{"filename":"notes.md","content":"# Notes","artifact_type":"file"}'

# Update artifact content (PUT)
curl.exe -s -X PUT "$BASE/artifacts/<artifact-id>/content" -H "Content-Type: application/json" -d '{"content":"new content"}'

# Delete artifact
curl.exe -s -X DELETE "$BASE/artifacts/<artifact-id>"

# Download all run artifacts as ZIP
curl.exe -s "$BASE/runs/<run-id>/artifacts/zip" -o artifacts.zip
```

## Research Workflow

1. **Create session:** `session create --name "Research Topic"`
2. **Import sources:** `source add --session <uuid> --file ./paper.pdf` (or via GUI drag-and-drop which auto-converts PDF/DOCX to markdown)
3. **Set persona:** `persona select --persona <id> --session <uuid>` (optional, sets AI behavior)
4. **Chat with AI:** `chat send --session <uuid> --message "Analyze the methodology"`
5. **Review artifacts:** `artifact list --session <uuid>` — AI responses and imports become artifacts
6. **Export results:** `artifact export --artifact <id> --out ./result.md`

## Common Pitfalls

1. **Port:** Backend is on **8001**, not 8000. Set `AGENTB_API_URL=http://localhost:8001/api/v1` if needed.
2. **PowerShell stderr:** CLI logs go to stderr. PowerShell shows these as red errors — they're not errors. Use `2>&1` and parse JSON from the output.
3. **Chat history:** `chat history` now fetches from the backend API. Note: the backend `/sessions/{uuid}/messages` endpoint may return empty if messages were only exchanged via the GUI chat interface (which uses `/api/chat` streaming).
4. **Session UUIDs:** Use full UUIDs (e.g., `a6444b3c-2a59-4b64-9da6-1450cb804a84`), not short IDs.
5. **Aliases:** `art` → `artifact`, `sess` → `session`, `ls` → `list`, `del` → `delete`, `src` → `source`
6. **Auto-session:** Use `--use-current-session` flag or `session use` to avoid passing `--session` every time.

## JSON Output Format

All `--json` responses follow this envelope:
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

Error responses:
```json
{
  "schema_version": "1.0",
  "ok": false,
  "result": null,
  "data": null,
  "error": {
    "code": "SESSION_NOT_FOUND",
    "message": "Session not found",
    "details": { "session": "..." }
  },
  "meta": {}
}
```
