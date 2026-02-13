# PRD: Workspace Persistence & Auto-Save System

**Product:** Agent-B Academic Research Workbench  
**Feature:** Workspace Persistence & Recovery  
**Version:** 1.0  
**Author:** 小蕾 (Lily)  
**Date:** 2026-02-11  
**Status:** Draft - Pending Review

---

## 1. Executive Summary

Agent-B is an AI-powered academic research workbench that helps researchers analyze papers, draft manuscripts, and manage research artifacts. As researchers invest significant time building their workspace—uploading papers, generating analyses, drafting content—**losing this work due to browser refresh, crash, or device switch is unacceptable**.

This PRD defines a **professional-grade persistence system** that ensures:
- Zero data loss under any circumstance
- Seamless cross-device continuity
- Automatic background saving
- Version history and recovery
- Project-level organization

---

## 2. Problem Statement

### Current State
| Data Type | Persistence | Risk |
|-----------|-------------|------|
| Sessions | ✅ Backend DB | Low |
| Backend Artifacts | ✅ Backend DB + Storage | Low |
| Chat-generated content | ❌ Memory only | **HIGH** - Lost on refresh |
| Focused artifacts | ❌ Memory only | Medium - Lost on refresh |
| Selected persona | ❌ Memory only | Low - Annoying to reselect |
| Text selections/annotations | ❌ Memory only | Medium - Lost on refresh |
| Draft edits in progress | ❌ Memory only | **HIGH** - Lost on refresh |

### User Pain Points
1. **"I spent 30 minutes getting AI to draft my methodology section, then accidentally refreshed—everything gone"**
2. **"I was working on my laptop, wanted to continue on desktop, had to start over"**
3. **"Browser crashed, lost my carefully organized artifact focus set"**
4. **"No way to save different 'workspaces' for different papers I'm writing"**

---

## 3. Goals & Success Metrics

### Goals
1. **Zero Data Loss**: Any user-generated or AI-generated content is automatically persisted
2. **Instant Recovery**: User can close browser, reopen, and continue exactly where they left off
3. **Cross-Device Sync**: Work seamlessly transfers between devices
4. **Version Safety**: Ability to recover from mistakes (undo, version history)
5. **Project Organization**: Researchers can maintain multiple independent projects

### Success Metrics
| Metric | Target |
|--------|--------|
| Data loss incidents | 0 per 1000 sessions |
| Recovery time (refresh → working state) | < 2 seconds |
| Auto-save latency | < 500ms after change |
| Cross-device sync time | < 5 seconds |
| User satisfaction (persistence) | > 4.5/5 |

---

## 4. User Stories

### P0 - Critical
- **US-1**: As a researcher, I want my AI-generated drafts automatically saved so I never lose work
- **US-2**: As a researcher, I want to refresh/close browser and return to exact same state
- **US-3**: As a researcher, I want to switch devices and continue my work seamlessly

### P1 - Important
- **US-4**: As a researcher, I want to organize my work into separate projects (one per paper)
- **US-5**: As a researcher, I want auto-save with visual confirmation so I know my work is safe
- **US-6**: As a researcher, I want to undo recent changes if I make a mistake
- **US-7**: As a researcher, I want to see version history of my artifacts

### P2 - Nice to Have
- **US-8**: As a researcher, I want to export my entire project for backup
- **US-9**: As a researcher, I want to share a project snapshot with collaborators
- **US-10**: As a researcher, I want offline mode that syncs when back online

---

## 5. Feature Specification

### 5.1 Data Model

#### 5.1.1 Project (New Entity)
```
Project
├── id: UUID
├── owner_id: UUID (User)
├── title: String
├── description: Text (optional)
├── created_at: Timestamp
├── updated_at: Timestamp
├── archived_at: Timestamp (nullable)
├── settings: JSONB
│   ├── auto_save_interval_ms: Integer (default: 5000)
│   ├── version_retention_days: Integer (default: 30)
│   └── default_persona_id: String (optional)
└── Sessions[] (1:N relationship)
```

#### 5.1.2 Session (Enhanced)
```
Session (existing, enhanced)
├── ... existing fields ...
├── project_id: UUID (FK → Project, nullable for backward compat)
├── workspace_state: JSONB
│   ├── focused_artifact_ids: UUID[]
│   ├── selected_persona_id: String
│   ├── text_selections: Selection[]
│   ├── panel_layout: Object
│   ├── scroll_positions: Object
│   └── last_active_artifact_id: UUID
├── workspace_state_version: Integer (optimistic locking)
└── last_auto_save_at: Timestamp
```

#### 5.1.3 Artifact (Enhanced)
```
Artifact (existing, enhanced)
├── ... existing fields ...
├── source: Enum ['upload', 'tool', 'chat', 'editor', 'import']
├── parent_artifact_id: UUID (nullable, for versioning)
├── version: Integer
├── is_draft: Boolean (unsaved editor changes)
├── draft_content: Text (nullable)
├── draft_updated_at: Timestamp (nullable)
└── checksum: String (content integrity)
```

#### 5.1.4 Artifact Version (New Entity)
```
ArtifactVersion
├── id: UUID
├── artifact_id: UUID (FK)
├── version: Integer
├── content_snapshot: Text/Binary
├── content_hash: String
├── created_at: Timestamp
├── created_by: Enum ['auto_save', 'manual_save', 'ai_edit']
├── change_summary: String (optional)
└── size_bytes: Integer
```

### 5.2 Auto-Save System

#### 5.2.1 Save Triggers
| Trigger | Debounce | Scope |
|---------|----------|-------|
| User stops typing | 2 seconds | Active artifact draft |
| User focuses out of editor | Immediate | Active artifact draft |
| AI response completes | Immediate | New artifact creation |
| Focus set changes | 500ms | Workspace state |
| Persona selection changes | Immediate | Workspace state |
| Tab/browser close (beforeunload) | Immediate | All pending changes |
| Periodic background | 30 seconds | Full workspace sync |

#### 5.2.2 Save Strategy
```
┌─────────────────────────────────────────────────────────┐
│                    SAVE PIPELINE                        │
├─────────────────────────────────────────────────────────┤
│  User Action                                            │
│       ↓                                                 │
│  Debounce Buffer (prevents save spam)                   │
│       ↓                                                 │
│  Dirty Check (skip if unchanged)                        │
│       ↓                                                 │
│  Optimistic UI Update ("Saving...")                     │
│       ↓                                                 │
│  Queue to Save Worker (non-blocking)                    │
│       ↓                                                 │
│  Batch API Call (combine multiple saves)                │
│       ↓                                                 │
│  Confirm UI Update ("Saved ✓")                          │
│       ↓                                                 │
│  [On Error] Retry with exponential backoff              │
│  [On Persistent Error] Store in localStorage + Alert    │
└─────────────────────────────────────────────────────────┘
```

#### 5.2.3 Conflict Resolution
When same artifact edited on multiple devices:
1. **Last-Write-Wins** (default): Most recent save overwrites
2. **Merge** (future): For text content, attempt 3-way merge
3. **Fork** (fallback): Create "Artifact (conflict copy)" if merge fails

### 5.3 Recovery System

#### 5.3.1 Session Recovery Flow
```
User opens Agent-B
       ↓
Check localStorage for pending offline changes
       ↓ (if any)
Sync offline changes to backend
       ↓
Fetch last session's workspace_state
       ↓
Restore:
  - Panel layout
  - Focused artifacts
  - Selected persona
  - Scroll positions
  - Open artifact in editor
       ↓
Fetch artifact drafts (if any unsaved)
       ↓
Show "Restored your workspace" toast
```

#### 5.3.2 Crash Recovery
- **beforeunload**: Save all dirty state to localStorage as emergency backup
- **On next load**: Detect unclean shutdown, offer "Recover unsaved changes?"
- **IndexedDB**: Store large content (artifact drafts) that exceed localStorage limits

### 5.4 Version History

#### 5.4.1 Automatic Versioning
- **Minor versions**: Every auto-save (kept for 24 hours, then pruned)
- **Major versions**: Explicit "Save" action or significant AI edit (kept per retention policy)
- **Snapshots**: Daily snapshot of each actively-edited artifact

#### 5.4.2 Version History UI
```
┌─ Version History: methodology.md ─────────────────┐
│                                                   │
│  ● Current version                      just now  │
│  ○ Auto-save                           2 min ago  │
│  ○ Auto-save                           5 min ago  │
│  ★ Manual save "Added results section"  1 hr ago  │
│  ○ AI edit "Expanded methodology"       2 hr ago  │
│  ★ Manual save "Initial draft"        yesterday   │
│                                                   │
│  [Preview] [Restore] [Compare]                    │
└───────────────────────────────────────────────────┘
```

### 5.5 Project Management

#### 5.5.1 Project Structure
```
Project: "PhD Thesis Chapter 3"
├── Sessions
│   ├── "Literature Review" (session)
│   ├── "Data Analysis" (session)
│   └── "Writing" (session)
├── Artifacts (shared across sessions)
│   ├── Papers/ (uploaded PDFs)
│   ├── Drafts/ (AI-generated & edited)
│   ├── Notes/ (user notes)
│   └── Exports/ (final outputs)
└── Settings
    ├── Default persona
    ├── Auto-save preferences
    └── Collaborators (future)
```

#### 5.5.2 Project Switcher UI
```
┌─ Projects ──────────────────────────────┐
│  🔵 PhD Thesis Chapter 3        Active  │
│     Last edited: 2 minutes ago          │
│                                         │
│  ○ Conference Paper (ICIS 2026)         │
│     Last edited: yesterday              │
│                                         │
│  ○ Grant Proposal                       │
│     Last edited: 3 days ago             │
│                                         │
│  [+ New Project]  [Archive]  [Export]   │
└─────────────────────────────────────────┘
```

---

## 6. API Specification

### 6.1 New Endpoints

#### Projects
```
POST   /api/v1/projects                    Create project
GET    /api/v1/projects                    List user's projects
GET    /api/v1/projects/{id}               Get project details
PATCH  /api/v1/projects/{id}               Update project
DELETE /api/v1/projects/{id}               Archive project
POST   /api/v1/projects/{id}/export        Export project as ZIP
```

#### Workspace State
```
GET    /api/v1/sessions/{id}/workspace     Get workspace state
PATCH  /api/v1/sessions/{id}/workspace     Update workspace state (partial)
POST   /api/v1/sessions/{id}/workspace/sync   Batch sync (multiple changes)
```

#### Artifact Versions
```
GET    /api/v1/artifacts/{id}/versions     List versions
GET    /api/v1/artifacts/{id}/versions/{v} Get specific version
POST   /api/v1/artifacts/{id}/restore/{v}  Restore to version
GET    /api/v1/artifacts/{id}/diff/{v1}/{v2}  Compare versions
```

#### Auto-Save
```
POST   /api/v1/sessions/{id}/autosave      Batch auto-save endpoint
  Body: {
    workspace_state: {...},           // Optional
    artifact_drafts: [                // Optional
      { artifact_id, draft_content }
    ],
    new_artifacts: [                  // Optional
      { display_name, content, source: "chat" }
    ]
  }
```

### 6.2 WebSocket Events (Real-time Sync)

```
// Server → Client
workspace_updated    { session_id, workspace_state, version }
artifact_saved       { artifact_id, version, saved_at }
conflict_detected    { artifact_id, server_version, client_version }

// Client → Server
subscribe_session    { session_id }
unsubscribe_session  { session_id }
```

---

## 7. UI/UX Specification

### 7.1 Save Status Indicator
```
┌─────────────────────────────────────────────┐
│  Header                      [💾 Saved ✓]   │  ← Always visible
└─────────────────────────────────────────────┘

States:
- "Saved ✓" (green) - All changes persisted
- "Saving..." (gray, animated) - Save in progress
- "Unsaved changes" (yellow) - Pending save
- "Offline - changes cached" (orange) - No connection
- "Save failed - retrying" (red) - Error state
```

### 7.2 Recovery Modal
```
┌─ Recover Your Work ─────────────────────────┐
│                                             │
│  ⚠️ We found unsaved changes from your      │
│  last session (2 minutes ago)               │
│                                             │
│  • 1 artifact with unsaved edits            │
│  • 3 focused artifacts                      │
│  • Persona: "The Drafter"                   │
│                                             │
│  [Recover All]  [Start Fresh]  [Review]     │
└─────────────────────────────────────────────┘
```

### 7.3 Version History Panel
Accessible via artifact context menu → "Version History"
(See Section 5.4.2 for mockup)

### 7.4 Settings: Auto-Save Preferences
```
┌─ Auto-Save Settings ────────────────────────┐
│                                             │
│  Auto-save: [✓] Enabled                     │
│                                             │
│  Save frequency:                            │
│  ○ Aggressive (every 2 seconds)             │
│  ● Normal (every 5 seconds)                 │
│  ○ Conservative (every 30 seconds)          │
│  ○ Manual only                              │
│                                             │
│  Version history retention:                 │
│  [30 days ▼]                                │
│                                             │
│  [Save Preferences]                         │
└─────────────────────────────────────────────┘
```

---

## 8. Technical Architecture

### 8.1 Frontend Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND                             │
├─────────────────────────────────────────────────────────┤
│  Zustand Store (in-memory)                              │
│  ├── workspaceState                                     │
│  ├── dirtyFlags (what needs saving)                     │
│  └── saveQueue                                          │
│           │                                             │
│           ▼                                             │
│  PersistenceManager (singleton)                         │
│  ├── debounceTimer                                      │
│  ├── saveWorker (Web Worker for non-blocking)           │
│  ├── offlineQueue (IndexedDB)                           │
│  └── conflictResolver                                   │
│           │                                             │
│           ▼                                             │
│  API Client (with retry logic)                          │
│           │                                             │
└───────────┼─────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────┐
│                    BACKEND                              │
├─────────────────────────────────────────────────────────┤
│  FastAPI Endpoints                                      │
│  ├── /autosave (batched saves)                          │
│  ├── /workspace (state CRUD)                            │
│  └── /versions (history)                                │
│           │                                             │
│           ▼                                             │
│  PostgreSQL                                             │
│  ├── sessions (with workspace_state JSONB)              │
│  ├── artifacts (with draft fields)                      │
│  ├── artifact_versions                                  │
│  └── projects                                           │
│           │                                             │
│           ▼                                             │
│  Object Storage (S3/MinIO)                              │
│  └── Artifact content & version snapshots               │
└─────────────────────────────────────────────────────────┘
```

### 8.2 Offline Support
```
┌─────────────────────────────────────────────────────────┐
│  OFFLINE PERSISTENCE LAYER                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  localStorage (5-10MB limit)                            │
│  └── Small state: workspace_state, preferences          │
│                                                         │
│  IndexedDB (unlimited)                                  │
│  └── Large content: artifact drafts, pending uploads    │
│                                                         │
│  Service Worker (future)                                │
│  └── Intercept failed requests, queue for retry         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 9. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Database schema changes (workspace_state, artifact drafts)
- [ ] Backend API: workspace state CRUD
- [ ] Backend API: artifact draft save/load
- [ ] Frontend: PersistenceManager service
- [ ] Frontend: Auto-save for artifact drafts
- [ ] Frontend: Save status indicator

### Phase 2: Recovery & Sync (Week 3)
- [ ] Session recovery on page load
- [ ] Crash recovery (beforeunload + localStorage)
- [ ] Cross-tab sync (BroadcastChannel API)
- [ ] Offline queue (IndexedDB)

### Phase 3: Version History (Week 4)
- [ ] Database: artifact_versions table
- [ ] Backend: version CRUD + diff API
- [ ] Frontend: Version history panel
- [ ] Frontend: Restore/compare functionality

### Phase 4: Projects (Week 5-6)
- [ ] Database: projects table
- [ ] Backend: project CRUD
- [ ] Frontend: Project switcher
- [ ] Frontend: Project settings
- [ ] Export/import functionality

### Phase 5: Polish (Week 7)
- [ ] Settings UI for auto-save preferences
- [ ] Performance optimization (batching, compression)
- [ ] Error handling & edge cases
- [ ] Documentation & testing

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Data loss during save failure | Critical | localStorage backup + retry queue |
| Merge conflicts across devices | High | Last-write-wins + conflict notification |
| Performance impact of frequent saves | Medium | Debouncing + batching + Web Worker |
| Storage costs for version history | Medium | Retention limits + compression |
| Offline changes lost if localStorage cleared | Medium | Prompt user to sync before clearing |

---

## 11. Open Questions

1. **Collaboration**: Should we support real-time collaboration (Google Docs style)? → Suggest deferring to v2
2. **Encryption**: Should artifact content be encrypted at rest? → Depends on deployment context
3. **Quota management**: How much storage per user/project? → Need to define tiers
4. **Export format**: ZIP with folder structure? Or custom format? → Suggest standard ZIP

---

## 12. Appendix

### A. Competitor Analysis
| Feature | Agent-B (proposed) | Notion | Overleaf | Obsidian |
|---------|-------------------|--------|----------|----------|
| Auto-save | ✅ 5s interval | ✅ Real-time | ✅ Real-time | ✅ On change |
| Version history | ✅ 30 days | ✅ 30 days (paid) | ✅ Unlimited | ❌ Plugin |
| Offline mode | ✅ IndexedDB | ✅ Limited | ❌ | ✅ Local-first |
| Cross-device | ✅ | ✅ | ✅ | ✅ (paid sync) |
| Project organization | ✅ | ✅ | ✅ | ✅ Vaults |

### B. Database Migration Plan
```sql
-- Phase 1 migrations
ALTER TABLE sessions ADD COLUMN workspace_state JSONB DEFAULT '{}';
ALTER TABLE sessions ADD COLUMN workspace_state_version INTEGER DEFAULT 1;
ALTER TABLE sessions ADD COLUMN last_auto_save_at TIMESTAMP;

ALTER TABLE artifacts ADD COLUMN source VARCHAR(20) DEFAULT 'upload';
ALTER TABLE artifacts ADD COLUMN is_draft BOOLEAN DEFAULT FALSE;
ALTER TABLE artifacts ADD COLUMN draft_content TEXT;
ALTER TABLE artifacts ADD COLUMN draft_updated_at TIMESTAMP;

-- Phase 3 migrations
CREATE TABLE artifact_versions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  artifact_id UUID REFERENCES artifacts(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  content_snapshot BYTEA,
  content_hash VARCHAR(64),
  created_at TIMESTAMP DEFAULT NOW(),
  created_by VARCHAR(20),
  change_summary TEXT,
  size_bytes INTEGER,
  UNIQUE(artifact_id, version)
);

-- Phase 4 migrations
CREATE TABLE projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID, -- REFERENCES users(id) when auth enabled
  title VARCHAR(255) NOT NULL,
  description TEXT,
  settings JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  archived_at TIMESTAMP
);

ALTER TABLE sessions ADD COLUMN project_id UUID REFERENCES projects(id);
```

---

**Document History**
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-11 | 小蕾 | Initial draft |

---

*Awaiting review from 老爷*
