# Textus Transparens (TT)

## 1. Introduction
Textus Transparens (TT) is an audit-trail-first qualitative analysis tool designed for researchers who demand rigorous transparency, reproducibility, and powerful insights. Whether you are conducting thematic analysis, grounded theory research, or literature reviews, TT provides a robust, command-line-driven environment to ingest sources, code text, apply AI-assisted analysis, and synthesize findings. Every action in TT is meticulously logged, ensuring that your research process is as transparent as your results.

## 2. Getting Started
TT is designed to be fast and accessible for your research workflows. 

**How to launch:**
- **Desktop Shortcut:** You can launch TT directly using the provided desktop shortcut if configured.
- **Batch Script:** Alternatively, navigate to the TT installation directory and run `launch_tt.bat` from your command prompt or terminal.

```cmd
C:\Users\thene\projects\tt> launch_tt.bat
```

## 3. The Research Workflow
TT supports a structured, multi-phase research workflow designed to guide you from raw data to rich, thematic reports.

### Phase 1: Ingestion
Begin by adding your raw qualitative data into your TT project.
- **Command:** `source add`
- **Details:** Import documents, transcripts, and notes. TT securely stores, parses, and indexes these sources for rapid retrieval.

### Phase 2: Coding
Analyze your data by applying codes to text segments.
- **Commands:** `code create`, `code apply`, `ai suggest`
- **Details:** Manually define and apply codes to your sources, or leverage AI to suggest potential codes based on the context of the text.

### Phase 3: Synthesis
Draw connections and build higher-level understanding.
- **Commands:** `memo create`, `case create`, `map theme create`
- **Details:** Write analytical memos, group related data into cases (e.g., participants, organizations), and map out relationships between codes and concepts.

### Phase 4: Reliability
Ensure the consistency and rigor of your coding.
- **Commands:** `irr sample`, `irr score`
- **Details:** Calculate and review inter-rater reliability scores to validate your coding framework across multiple researchers.

### Phase 5: Reporting
Export your findings into structured formats.
- **Commands:** `report theme-pack`, `report codebook`, `report matrix`
- **Details:** Generate comprehensive theme packs, codebooks, and analytic matrices. Supporting exports to Markdown, CSV, Word, PDF, and Excel.

### Phase 6: Theory (Academic Excellence)
Advanced theoretical analysis and visualization.
- **Commands:** `framework create`, `ai sense`, `report evolution`, `export gp-viz`
- **Details:** Apply theoretical frameworks to your data, identify conceptual tensions using AI, generate narrative audit trails of theory evolution, and export 3D semantic landscapes.

## 4. Command Reference

### Project (`project`)
Manage TT projects.
- `project init`: Initialize a new TT project. Creates the project directory structure, config, and database.
- `project list`: List all TT projects in the workspace.
- `project reindex`: Rebuild the full-text search (FTS) index for the current project.
- `project check`: Check the integrity of the project database and files.
- `project finalize`: Finalize the project and log the event.

### Source (`source`)
Manage TT sources.
- `source add`: Add a new source to the current project.

### Code (`code`)
Manage TT codes.
- `code create`: Create a new code.
- `code list`: List all codes. Use `--all` to see deprecated/merged codes.
- `code apply`: Apply a code to a specific extract of a source.
- `code rename`: Rename an existing code.
- `code delete`: Delete (deprecate) a code.
- `code merge`: Merge multiple codes into a new code.
- `code split`: Split a code into multiple new codes.
- `code intersect`: Find extracts that contain both of two specified codes.

### Search (`search`)
Search across the project.
- `search text`: Search for a string across all canonical Markdown source files.
- `search code`: Show all extracts assigned to a specific code.
- `search cross`: Identify sources where both codes appear.

### AI (`ai`)
AI-assisted semantic coding.
- `ai suggest`: Run AI semantic suggestion pass. Supports `--provider` (gemini, ollama) and `--model`.
- `ai sense`: Analyze extracts for conceptual overlaps and tensions within a theoretical framework.
- `ai sense-list`: List all AI-identified theoretical intersections.

### Review (`review`)
Review AI suggestions.
- `review list`: List AI suggestions awaiting review.
- `review accept`: Accept an AI suggestion and convert it to a CodeAssignment.
- `review reject`: Reject an AI suggestion.

### Memo (`memo`)
Manage TT memos.
- `memo create`: Create a new memo.
- `memo list`: List all memos.
- `memo delete`: Delete a memo.

### Case (`case`)
Manage TT cases.
- `case create`: Create a new case.
- `case list`: List all cases.
- `case delete`: Delete a case.
- `case assign`: Assign a source or extract to a specific case.

### Framework (`framework`)
Manage Theoretical Frameworks (v1.1).
- `framework create`: Create a new theoretical framework.
- `framework add-dim`: Add a dimension to a framework and optionally map it to a code.
- `framework list`: List all theoretical frameworks.

### Map (`map`)
Manage TT maps (clusters and themes).
- **Cluster** (`map cluster`)
  - `map cluster create`: Create a new cluster.
  - `map cluster list`: List all clusters.
  - `map cluster delete`: Delete a cluster.
  - `map cluster assign`: Assign a code to a cluster.
  - `map cluster unassign`: Unassign a code from a cluster.
- **Theme** (`map theme`)
  - `map theme create`: Create a new theme.
  - `map theme list`: List all themes.
  - `map theme delete`: Delete a theme.
  - `map theme assign-code`: Assign a code to a theme.
  - `map theme unassign-code`: Unassign a code from a theme.
  - `map theme assign-cluster`: Assign a cluster to a theme.
  - `map theme unassign-cluster`: Unassign a cluster from a theme.

### Gut (`gut`)
Manage gut feelings and judgement notes.
- `gut tag`: Tag an extract with a JudgementNote.
- `gut list`: List JudgementNotes (Gut tags).

### Report (`report`)
Generate project reports.
- `report codebook`: Generate the codebook report. Supports `--format` (md, csv, xlsx, docx, pdf).
- `report extracts`: Generate the extracts report. Supports `--format`.
- `report matrix`: Generate the matrix analytics report. Use `--advanced` for Density/Breadth analysis.
- `report theme-pack`: Generate a theme evidence pack.
- `report evolution`: Generate a narrative audit trail of how the theory evolved (v1.1).

### Export (`export`)
Export project data (v1.1).
- `export gp-viz`: Export project as a semantic landscape for GP-Viz 3D visualization.

### Snapshot (`snapshot`)
Manage project snapshots.
- `snapshot create`: Create a versioned bundle of the current database and canonical files.
- `snapshot restore`: Restore a specific snapshot, replacing current DB and canonical files.

### IRR (`irr`)
Manage Inter-Rater Reliability (IRR).
- `irr sample`: Generate a random sample of extracts for blind-coding.
- `irr score`: Calculate and display Cohen's Kappa score for two coders.

## 5. Technical Notes
TT is built on a robust and scalable architecture to handle large qualitative datasets reliably:

- **Project Structure:** Each project is encapsulated in its own directory, containing the database, exports, logs, and source files.
- **SQLite DB:** All data, metadata, and relationships are stored locally in a lightweight, high-performance SQLite database.
- **FTS5 Search:** TT utilizes SQLite's FTS5 extension to provide lightning-fast full-text search capabilities across all ingested sources and coded segments.
- **Audit Logs:** Every command executed and change made is recorded in an immutable audit log, establishing a complete chain of custody for your analysis.
- **Hardware Acceleration:** TT is optimized for modern hardware. It leverages **AMD Ryzen AI (NPU)** and **Radeon GPU (DirectML)** for semantic computations. For maximum stability with the BGE-M3 model, a high-performance CPU-only mode is also available.
- **Local LLM Support:** TT supports local model inference via **Ollama**, allowing researchers to run models like DeepSeek-R1 and Llama 3.1 entirely on-premise for enhanced privacy.
- **Structural Anchor System:** Sources are parsed and structurally anchored (e.g., tracking paragraphs, lines, or speaker turns) to ensure that codes precisely reference the original context even as analysis evolves.

## 6. Safety & Reproducibility
Research data is invaluable. TT protects your work through a comprehensive snapshotting system:

- **Snapshots:** Use the `snapshot` commands to capture the exact state of your project at any point in time. 
- **Reproducibility:** Snapshots not only serve as backups but also allow you to revert to previous states to test different analytical paths or reproduce past findings, guaranteeing the integrity of your research process.
