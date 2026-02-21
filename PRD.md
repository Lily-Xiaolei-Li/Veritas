# Product Requirements Document (PRD)

## Veritas — Local-First AI Workspace Platform

**Version:** 2.0  
**Codename:** Veritas  
**Last Updated:** January 26, 2026  
**Author:** Lily Xiaolei Li

**Audience:**

- Developers building domain-specific AI applications
- Teams wanting a privacy-preserving AI workspace foundation
- Agentic coding systems (Claude Code, Cursor, etc.)

---

## Changelog

### Version 2.0 (January 26, 2026)

**Major Revision: Platform Pivot**

Agent B is now positioned as an open-source foundation for building local-first AI workspaces, rather than a fully-featured "cognitive colleague." This revision:

- Simplifies the vision to focus on platform capabilities
- Removes multi-brain escalation architecture (archived for future extensions)
- Removes complex memory/trust/provenance systems (archived)
- Adds Extension Points documentation
- Targets a v1.0 stable release

The original cognitive workbench vision remains valid for domain-specific applications built on this platform.

### Version 1.1 (January 26, 2026)

- Added Multi-Brain Architecture with role-based collaboration
- Defined Brain 1/2/3 responsibilities and escalation triggers

---

## 1. Concept & Vision

### 1.1 What Is Veritas?

Veritas is an open-source foundation for building local-first, privacy-preserving AI workspaces. It provides the infrastructure that developers need to create domain-specific AI assistants without starting from scratch.

Veritas is a **platform**, not a product. It handles the common concerns—LLM integration, safe code execution, document processing, session management, and a flexible UI shell—so builders can focus on their domain-specific logic.

### 1.2 Why Veritas Exists

Building AI applications requires solving the same problems repeatedly:

- Connecting to various LLM providers (local and cloud)
- Executing code safely in sandboxed environments
- Processing common document formats
- Managing conversation history and sessions
- Providing a usable interface for interaction

Veritas solves these once, well, so developers can build specialized applications on top.

### 1.3 Core Principles

1. **Privacy First.** Data stays local by default. No telemetry, no cloud requirements.
2. **Model Agnostic.** Works with local models (Ollama) or cloud APIs (Gemini, OpenRouter, Anthropic).
3. **Safety by Default.** Code execution is sandboxed. Dangerous operations require approval.
4. **Extensible by Design.** Clear extension points for tools, UI panels, and providers.
5. **Simplicity Over Features.** Ship less, ship well. Complex features belong in domain applications.

---

## 2. Platform Capabilities

Agent B provides these foundational capabilities:

| Capability | Description |
|------------|-------------|
| LLM Integration | Connect to any LLM via provider abstraction (Ollama, Gemini, OpenRouter) |
| Safe Execution | Run code locally with strict safety controls (no Docker dependency in this repo) |
| Document Processing | Read and write common formats (Word, Excel, PDF) |
| Session Management | Persistent conversations that survive restarts |
| Workbench UI | Three-panel interface for reasoning, artifacts, and console output |
| History & Audit | Track what the AI did, when, and why |

### 2.1 What Agent B Does NOT Do

To maintain focus, Agent B intentionally excludes:

- **Multi-agent orchestration** — Build this in your domain application
- **Complex memory systems** — Session history is enough for the platform
- **Domain-specific reasoning** — Your application defines its own logic
- **Personality/mode switching** — Application-level concern
- **Vector search/RAG** — Add via extension if needed

These features can be built on top of Agent B for specific use cases.

---

## 3. Architecture

### 3.1 System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent B Platform                          │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React/Next.js)                                    │
│  ┌─────────────┬─────────────┬─────────────┐                │
│  │  Reasoning  │  Artifacts  │   Console   │                │
│  │    Panel    │    Panel    │    Panel    │                │
│  └─────────────┴─────────────┴─────────────┘                │
├─────────────────────────────────────────────────────────────┤
│  API Gateway (FastAPI)                                       │
│  - Sessions, Messages, Runs                                  │
│  - Authentication (optional)                                 │
│  - File & Artifact management                                │
├─────────────────────────────────────────────────────────────┤
│  Core Services                                               │
│  ┌──────────────┬──────────────┬──────────────┐             │
│  │ LLM Provider │  Executor    │  Document    │             │
│  │  Abstraction │ (Local Exec) │  Processor   │             │
│  └──────────────┴──────────────┴──────────────┘             │
├─────────────────────────────────────────────────────────────┤
│  Storage (PostgreSQL)                                        │
│  - Sessions, Messages, Runs, Events, Audit Log              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Technology Stack

| Layer | Technology | Status |
|-------|------------|--------|
| Frontend | React 18, Next.js 14, Tailwind CSS 3 | Complete |
| API Gateway | FastAPI 0.110 | Complete |
| LLM Providers | Ollama, Gemini, OpenRouter, Mock | Complete |
| Execution | Local execution (no Docker) | Complete |
| Storage | PostgreSQL 16, SQLAlchemy 2 | Complete |
| Documents | python-docx, openpyxl, PyMuPDF | Planned |

### 3.3 LLM Provider Abstraction

All LLM interactions go through a provider abstraction layer:

```python
# Unified interface for all providers
response = await llm_complete(
    provider="ollama",  # or "gemini", "openrouter"
    model="qwen3:32b",
    messages=[{"role": "user", "content": "Hello"}],
    options=LLMOptions(temperature=0.7)
)
```

**Supported Providers:**

| Provider | Use Case | Cost |
|----------|----------|------|
| Ollama | Local inference, privacy-first | Free (your hardware) |
| Gemini | Cloud generalist, multimodal | Pay per token |
| OpenRouter | Access to many models | Pay per token |
| Mock | Testing and development | Free |

---

## 4. User Interface

### 4.1 Workbench Layout

Agent B uses a three-panel workbench interface:

```
+----------------------------------------------------------+
|  Reasoning Panel          |  Artifacts Panel             |
|  - Chat history           |  - Documents                 |
|  - Streaming responses    |  - Generated files           |
|  - Tool invocations       |  - Downloads                 |
|---------------------------|------------------------------|
|  Console Panel                                           |
|  - Execution logs         |  - Events          |  Errors |
+----------------------------------------------------------+
|  [Kill Switch]                         [Session: #42]    |
+----------------------------------------------------------+
```

### 4.2 Key UI Features

| Feature | Description |
|---------|-------------|
| Token Streaming | Real-time display of LLM output |
| Tool Events | Live view of tool invocations in Console |
| Artifact Management | View, preview, and download generated files |
| Session Persistence | Sessions survive browser refresh and restart |
| Kill Switch | Terminate execution immediately |

### 4.3 Kill Switch

The Kill Switch is a critical safety feature:

- Always visible, fixed position
- Terminates active execution within 2 seconds
- Cancels pending LLM API calls
- Records termination with timestamp
- Requires deliberate action (two-click confirmation)

---

## 5. Safety & Security

### 5.1 Execution Sandbox

In this repository, code execution runs **without Docker** and is restricted by safety controls:

- **No network by default** (unless explicitly allowed)
- **Workspace-only file access** (no access to secrets/config directories)
- **Timeouts and output limits**
- **Command blocklist + high-risk approvals**

> Note: Containerized execution can be added by downstream deployers if desired, but it is out of scope for the core repo to keep development/testing fast and simple.

### 5.2 Command Safety

**Blocked by default:**

- `rm -rf /` and destructive commands
- Network tools (`curl`, `wget`) unless explicitly allowed
- Package installation outside designated environment
- Access to `.env`, credentials, or key files
- `sudo` or privilege escalation

**Approval required for:**

- Commands matching high-risk patterns
- Network access to non-allowlisted domains
- Operations exceeding cost thresholds

### 5.3 Output Redaction

Before displaying or logging, Agent B scans for:

- API keys (common patterns like `AKIA...`, `sk-...`)
- Passwords and secrets
- Private keys

Detected secrets are replaced with `[REDACTED]`.

### 5.4 Authentication

- **Local deployment:** Optional password protection
- **API access:** Bearer tokens with configurable expiration
- **API keys:** Encrypted at rest, never logged

---

## 6. Extension Points

Agent B is designed for extensibility. Here's how to build on it:

### 6.1 Custom LLM Providers

Implement the `LLMProvider` interface to add new model sources:

```python
class MyProvider(LLMProvider):
    async def complete(self, messages, options) -> LLMResponse:
        # Your implementation
        pass

    async def health_check(self) -> bool:
        # Return True if provider is available
        pass
```

### 6.2 Custom Tools

Add tools to the executor by registering them:

```python
@register_tool("my_tool")
async def my_tool(args: dict) -> ToolResult:
    # Your tool logic
    return ToolResult(success=True, output="...")
```

### 6.3 Custom UI Panels

The React frontend uses a panel system that can be extended:

```typescript
// Replace or extend panels in the workbench
<WorkbenchLayout
  reasoning={<CustomReasoningPanel />}
  artifacts={<MyDomainPanel />}
  console={<ConsolePanel />}
/>
```

### 6.4 Domain Context Injection

Inject domain-specific context into the agent loop:

```python
# Example: Audit domain context
context = DomainContext(
    system_prompt="You are an audit assistant...",
    tools=["workpaper_parser", "standard_lookup"],
    knowledge_base=audit_standards_path
)
```

---

## 7. Example Applications

Agent B can serve as the foundation for:

| Application | Description |
|-------------|-------------|
| **Agent B Auditor** | AI-powered audit workpaper assistant |
| **Agent B Researcher** | Literature review and citation manager |
| **Agent B Analyst** | Data analysis and visualization workbench |
| **Agent B Writer** | Long-form content assistant with document output |

Each application would add domain-specific:
- Tools (e.g., workpaper parser, citation formatter)
- UI panels (e.g., document index, reference manager)
- Context (e.g., audit standards, style guides)
- Workflows (e.g., review cycles, approval chains)

---

## 8. Data Residency & Privacy

### 8.1 Local by Default

All data remains on your machine:

- Session history stored in local PostgreSQL
- Documents processed locally
- Artifacts saved to local filesystem

### 8.2 External Calls

External network calls are made only for:

- LLM API requests (when using cloud providers)
- Explicitly configured external tools

**Air-gapped mode:** Use Ollama for fully offline operation.

---

## 9. Operational Basics

### 9.1 Health Monitoring

The `/health` endpoint reports:

- Database connectivity
- Resource status (disk, memory)

### 9.2 Audit Logging

All significant actions are logged:

- Session creation/deletion
- Message submissions
- Tool executions (command, result, duration)
- Terminations

Logs are stored in PostgreSQL with configurable retention.

---

## 10. License

Agent B is released under the **MIT License**.

You are free to use, modify, and distribute Agent B for any purpose, including commercial applications.

---

## Appendix A: Archived Ideas

The following concepts from the original "cognitive workbench" vision are preserved here for future reference. They may be implemented as extensions or in domain-specific applications:

### Multi-Brain Escalation

A layered reasoning system where:
- Brain 1 (Coordinator): Task classification, local execution
- Brain 2 (Manager): Complex reasoning, broad knowledge
- Brain 3 (Specialist): Deep domain expertise

### Circles of Consultation

Ordered knowledge sources:
1. Self Memory (past runs, patterns)
2. Institutional Memory (local documents)
3. External Authorities (APIs, documentation)
4. Human Authority (Agent A)

### Trust Ledger

Reliability tracking for sources, tools, and methods with:
- Trust scores (0.0–1.0)
- Success/failure counts
- Time-based decay toward neutral

### Provenance System

Metadata tracking for claims:
- Source attribution
- Extraction method
- Confidence scores
- Model and prompt versioning

### Decision Packs

Structured escalation to humans including:
- Objective and attempts
- Failure analysis
- Options with risk assessment
- Specific questions for judgment

These ideas remain valid for sophisticated domain applications but are beyond the scope of the platform foundation.

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| Agent A | The human user |
| Agent B | This platform |
| Artifact | A file produced by the agent |
| Provider | An LLM backend (Ollama, Gemini, etc.) |
| Run | A single task execution |
| Session | A conversation context containing messages and runs |
| Tool | A capability the agent can invoke |
| Workbench | The three-panel UI interface |

---

**End of PRD**
