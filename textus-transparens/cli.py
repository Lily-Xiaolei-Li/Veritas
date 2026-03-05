import os
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import typer
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from rich.console import Console
from rich.table import Table

# Import models to initialize the database schema and insert the project
from models import Base, Project as DBProject

# Create Typer apps
app = typer.Typer(
    help="Textus Transparens (TT) - CLI-first qualitative analysis workbench",
    no_args_is_help=True
)
project_app = typer.Typer(help="Manage TT projects")
app.add_typer(project_app, name="project", no_args_is_help=True)

source_app = typer.Typer(help="Manage TT sources")
app.add_typer(source_app, name="source", no_args_is_help=True)

code_app = typer.Typer(help="Manage TT codes")
app.add_typer(code_app, name="code", no_args_is_help=True)

search_app = typer.Typer(help="Search across the project")
app.add_typer(search_app, name="search", no_args_is_help=True)

ai_app = typer.Typer(help="AI-assisted semantic coding")
app.add_typer(ai_app, name="ai", no_args_is_help=True)

review_app = typer.Typer(help="Review AI suggestions")
app.add_typer(review_app, name="review", no_args_is_help=True)

memo_app = typer.Typer(help="Manage TT memos")
app.add_typer(memo_app, name="memo", no_args_is_help=True)

case_app = typer.Typer(help="Manage TT cases")
app.add_typer(case_app, name="case", no_args_is_help=True)

framework_app = typer.Typer(help="Manage Theoretical Frameworks")
app.add_typer(framework_app, name="framework", no_args_is_help=True)

map_app = typer.Typer(help="Manage TT maps (clusters and themes)")
app.add_typer(map_app, name="map", no_args_is_help=True)

cluster_app = typer.Typer(help="Manage clusters")
map_app.add_typer(cluster_app, name="cluster", no_args_is_help=True)

theme_app = typer.Typer(help="Manage themes")
map_app.add_typer(theme_app, name="theme", no_args_is_help=True)

gut_app = typer.Typer(help="Manage gut feelings and judgement notes")
app.add_typer(gut_app, name="gut", no_args_is_help=True)

report_app = typer.Typer(help="Generate project reports")
app.add_typer(report_app, name="report", no_args_is_help=True)

export_app = typer.Typer(help="Export project data in various formats")
app.add_typer(export_app, name="export", no_args_is_help=True)

snapshot_app = typer.Typer(help="Manage project snapshots")
app.add_typer(snapshot_app, name="snapshot", no_args_is_help=True)

irr_app = typer.Typer(help="Manage Inter-Rater Reliability (IRR)")
app.add_typer(irr_app, name="irr", no_args_is_help=True)

console = Console()

def get_workspace_dir() -> Path:
    """Get the workspace directory, defaulting to current working directory."""
    return Path(os.environ.get("TT_WORKSPACE", os.getcwd()))

def get_current_project_dir() -> Path:
    """Get the current project directory based on tt.yml presence."""
    cwd = Path(os.getcwd())
    if (cwd / "tt.yml").exists():
        return cwd
    # fallback to check if we are in workspace root and only have one project
    workspace = get_workspace_dir()
    projects_dir = workspace / "projects"
    if projects_dir.exists():
        projects = [p for p in projects_dir.iterdir() if p.is_dir() and (p / "tt.yml").exists()]
        if len(projects) == 1:
            return projects[0]
        # Default to 'test_project' if it exists and no other project context is clear
        test_project_dir = projects_dir / "test_project"
        if test_project_dir.exists() and (test_project_dir / "tt.yml").exists():
            return test_project_dir
    
    console.print("[bold red]Error:[/bold red] Must run from within a project directory (containing tt.yml), have exactly one project, or have a 'test_project'.")
    raise typer.Exit(code=1)

from source_manager import add_source

def log_command(project_dir: Path, command: str, **kwargs):
    log_file = project_dir / "logs" / "tt_commands.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        **kwargs
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

@source_app.command("add")
def source_add(
    path: str = typer.Argument(..., help="Path to the source file to add")
):
    """
    Add a new source to the current project.
    """
    project_dir = get_current_project_dir()
    try:
        source_id = add_source(project_dir, path)
        
        # Log command
        log_command(project_dir, f"source add {path}", source_id=source_id)
        
        # Rich output
        file_path = Path(path)
        file_size = file_path.stat().st_size
        
        table = Table(title="Source Added Successfully")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("ID", source_id)
        table.add_row("Name", file_path.name)
        table.add_row("Type", file_path.suffix.lstrip(".").lower() or "unknown")
        table.add_row("Size", f"{file_size} bytes")
        
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to add source: {e}")
        raise typer.Exit(code=1)

# --- Architecture for Pluggable AI Backends ---
class AIProviderPlugin:
    """Base interface for all AI backends."""
    def configure(self, config: dict):
        raise NotImplementedError
        
    def suggest(self, context: dict) -> list:
        raise NotImplementedError

class DummyProvider(AIProviderPlugin):
    """A dummy provider for testing and offline usage."""
    def configure(self, config: dict):
        pass
        
    def suggest(self, context: dict) -> list:
        return [{"code": "example", "rationale": "dummy rationale"}]

class AIBackendRegistry:
    """Registry to manage available AI backends."""
    def __init__(self):
        self._providers = {}
        
    def register(self, name: str, provider_cls):
        self._providers[name] = provider_cls
        
    def get_provider(self, name: str) -> AIProviderPlugin:
        if name not in self._providers:
            raise ValueError(f"AI provider '{name}' not found.")
        return self._providers[name]()

# Initialize registry and register built-in providers
ai_registry = AIBackendRegistry()
ai_registry.register("dummy", DummyProvider)
# Future providers can be registered here or via entry points
# ai_registry.register("openai", OpenAIProvider)
# ai_registry.register("anthropic", AnthropicProvider)

# --- CLI Commands ---

@project_app.command("init")
def project_init(
    name: str = typer.Argument(..., help="The name of the new project"),
    description: str = typer.Option("", help="Optional description of the project"),
    ai_backend: str = typer.Option("dummy", help="Default AI backend to use for this project")
):
    """
    Initialize a new TT project.
    
    Creates the project directory structure, tt.yml config, and SQLite database.
    """
    workspace = get_workspace_dir()
    project_dir = workspace / "projects" / name
    
    if project_dir.exists():
        console.print(f"[bold red]Error:[/bold red] Project '{name}' already exists at {project_dir}.")
        raise typer.Exit(code=1)
        
    # 1. Create folder structure defined in PRD Section 6.2
    folders = [
        "db",
        "sources",
        "codebook",
        "cases",
        "runs/ai",
        "reports",
        "exports",
        "snapshots",
        "logs"
    ]
    for folder in folders:
        (project_dir / folder).mkdir(parents=True, exist_ok=True)
        
    # 2. Write configuration (tt.yml)
    config = {
        "project": {
            "name": name,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "ai_backend": ai_backend
        }
    }
    with open(project_dir / "tt.yml", "w") as f:
        yaml.dump(config, f, sort_keys=False)
        
    # 3. Initialize SQLite database and models
    db_path = project_dir / "db" / "tt.sqlite"
    engine = create_engine(f"sqlite:///{db_path}")
    
    # Create all tables defined in models.py
    Base.metadata.create_all(engine)
    
    # Insert the primary project record into the db
    with Session(engine) as session:
        new_proj = DBProject(name=name, description=description)
        session.add(new_proj)
        session.commit()
        
    from search_manager import setup_fts
    setup_fts(project_dir)
        
    # 4. Initialize the append-only command log
    with open(project_dir / "logs" / "tt_commands.jsonl", "w") as f:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": "project init",
            "project_name": name,
            "ai_backend": ai_backend
        }
        f.write(json.dumps(log_entry) + "\n")
        
    console.print(f"[bold green]Success:[/bold green] Project '{name}' initialized successfully.")
    console.print(f"Location: {project_dir}")

@project_app.command("list")
def project_list():
    """
    List all TT projects in the workspace.
    """
    workspace = get_workspace_dir()
    projects_dir = workspace / "projects"
    
    if not projects_dir.exists():
        console.print("[yellow]No projects directory found in the workspace.[/yellow]")
        return
        
    table = Table(title="Workspace Projects")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("AI Backend", style="magenta")
    table.add_column("DB Status", style="blue")
    table.add_column("Description", style="green")
    
    has_projects = False
    for item in projects_dir.iterdir():
        if item.is_dir():
            has_projects = True
            config_file = item / "tt.yml"
            db_file = item / "db" / "tt.sqlite"
            
            ai_backend = "unknown"
            description = ""
            db_status = "OK" if db_file.exists() else "Missing"
            
            if config_file.exists():
                try:
                    with open(config_file, "r") as f:
                        config = yaml.safe_load(f)
                        if config and "project" in config:
                            ai_backend = config["project"].get("ai_backend", "unknown")
                            description = config["project"].get("description", "")
                except Exception:
                    description = "[red]Error reading tt.yml[/red]"
            
            table.add_row(item.name, ai_backend, db_status, description)
            
    if not has_projects:
        console.print("No projects found.")
    else:
        console.print(table)

@project_app.command("reindex")
def project_reindex_cmd():
    """
    Rebuild the full-text search (FTS) index for the current project.
    """
    project_dir = get_current_project_dir()
    try:
        from search_manager import reindex_project
        reindex_project(project_dir)
        log_command(project_dir, "project reindex")
        console.print("[bold green]Success:[/bold green] Reindexed project full-text search.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to reindex project: {e}")
        raise typer.Exit(code=1)

from code_manager import create_code, list_codes, apply_code, rename_code, delete_code

@code_app.command("create")
def code_create(
    name: str = typer.Argument(..., help="Name of the code"),
    parent_id: Optional[int] = typer.Option(None, "--parent", "-p", help="ID of the parent code"),
    definition: Optional[str] = typer.Option(None, "--def", "-d", help="Definition of the code")
):
    """Create a new code."""
    project_dir = get_current_project_dir()
    try:
        code_id = create_code(project_dir, name, parent_id, definition)
        log_command(project_dir, f"code create {name}", code_id=code_id, parent_id=parent_id)
        console.print(f"[bold green]Success:[/bold green] Created code '{name}' with ID {code_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to create code: {e}")
        raise typer.Exit(code=1)

@code_app.command("list")
def code_list(
    show_all: bool = typer.Option(False, "--all", "-a", help="Show all codes, including deprecated and merged/split codes")
):
    """List all codes."""
    project_dir = get_current_project_dir()
    try:
        codes = list_codes(project_dir, show_all=show_all)
        table = Table(title="Codebook")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Parent ID", style="blue")
        table.add_column("Definition", style="green")
        table.add_column("Status", style="yellow")
        
        for c in codes:
            table.add_row(
                str(c["code_id"]), 
                c["name"], 
                str(c["parent_code_id"]) if c["parent_code_id"] else "", 
                c["definition"] or "",
                c["status"] or "active"
            )
        console.print(table)
        log_command(project_dir, f"code list{' --all' if show_all else ''}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to list codes: {e}")
        raise typer.Exit(code=1)

@code_app.command("apply")
def code_apply(
    code_id: int = typer.Argument(..., help="ID of the code to apply"),
    source_id: int = typer.Argument(..., help="ID of the source"),
    anchor: str = typer.Argument(..., help="Anchor of the extract (e.g., p:12|h:Methods)"),
    text_span: str = typer.Option("", "--text", "-t", help="Text span of the extract")
):
    """Apply a code to a specific extract of a source."""
    project_dir = get_current_project_dir()
    try:
        assignment_id = apply_code(project_dir, code_id, source_id, anchor, text_span)
        log_command(project_dir, f"code apply {code_id} {source_id} {anchor}", assignment_id=assignment_id)
        console.print(f"[bold green]Success:[/bold green] Applied code {code_id} to source {source_id} at '{anchor}'. Assignment ID: {assignment_id}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to apply code: {e}")
        raise typer.Exit(code=1)

@code_app.command("rename")
def code_rename(
    code_id: int = typer.Argument(..., help="ID of the code to rename"),
    new_name: str = typer.Argument(..., help="New name for the code")
):
    """Rename an existing code."""
    project_dir = get_current_project_dir()
    try:
        rename_code(project_dir, code_id, new_name)
        log_command(project_dir, f"code rename {code_id} {new_name}")
        console.print(f"[bold green]Success:[/bold green] Renamed code {code_id} to '{new_name}'.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to rename code: {e}")
        raise typer.Exit(code=1)

@code_app.command("delete")
def code_delete(
    code_id: int = typer.Argument(..., help="ID of the code to delete (mark deprecated)")
):
    """Delete (deprecate) a code."""
    project_dir = get_current_project_dir()
    try:
        delete_code(project_dir, code_id)
        log_command(project_dir, f"code delete {code_id}")
        console.print(f"[bold green]Success:[/bold green] Deleted code {code_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to delete code: {e}")
        raise typer.Exit(code=1)

from code_manager import merge_codes, split_code

@code_app.command("merge")
def code_merge_cmd(
    source_ids: str = typer.Argument(..., help="Comma-separated list of code IDs to merge"),
    target_name: str = typer.Argument(..., help="Name of the new merged code"),
    definition: Optional[str] = typer.Option(None, help="Definition of the new code")
):
    """Merge multiple codes into a new code."""
    project_dir = get_current_project_dir()
    try:
        ids = [int(i.strip()) for i in source_ids.split(",")]
        new_id = merge_codes(project_dir, ids, target_name, definition)
        log_command(project_dir, f"code merge {source_ids} into {target_name}", new_code_id=new_id)
        console.print(f"[bold green]Success:[/bold green] Merged codes into new code '{target_name}' with ID {new_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to merge codes: {e}")
        raise typer.Exit(code=1)

@code_app.command("split")
def code_split_cmd(
    source_id: int = typer.Argument(..., help="ID of the code to split"),
    new_names: str = typer.Argument(..., help="Comma-separated names of new codes")
):
    """Split a code into multiple new codes."""
    project_dir = get_current_project_dir()
    try:
        names = [n.strip() for n in new_names.split(",")]
        new_ids = split_code(project_dir, source_id, names)
        log_command(project_dir, f"code split {source_id} into {new_names}", new_code_ids=new_ids)
        console.print(f"[bold green]Success:[/bold green] Split code {source_id} into new codes with IDs: {new_ids}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to split code: {e}")
        raise typer.Exit(code=1)

@code_app.command("intersect")
def code_intersect_cmd(
    code_a: int = typer.Argument(..., help="ID of the first code"),
    code_b: int = typer.Argument(..., help="ID of the second code")
):
    """Find extracts that contain both codes."""
    project_dir = get_current_project_dir()
    try:
        from sqlalchemy import create_engine, and_
        from sqlalchemy.orm import Session
        from models import CodeAssignment, Extract
        
        db_path = project_dir / "db" / "tt.sqlite"
        engine = create_engine(f"sqlite:///{db_path}")
        
        with Session(engine) as session:
            # Query extracts that have both codes
            # Subquery to get extract IDs for code A
            eids_a = session.query(CodeAssignment.extract_id).filter_by(code_id=code_a).all()
            eids_a = [id[0] for id in eids_a]
            
            # Subquery to get extract IDs for code B
            eids_b = session.query(CodeAssignment.extract_id).filter_by(code_id=code_b).all()
            eids_b = [id[0] for id in eids_b]
            
            common_ids = set(eids_a).intersection(eids_b)
            
            if not common_ids:
                console.print(f"No extracts found containing both code {code_a} and {code_b}.")
                return
                
            extracts = session.query(Extract).filter(Extract.extract_id.in_(common_ids)).all()
            
            table = Table(title=f"Code Intersections (Code {code_a} & {code_b})")
            table.add_column("Extract ID", style="cyan")
            table.add_column("Text Span", style="green")
            
            for e in extracts:
                table.add_row(str(e.extract_id), e.text_span[:100] + "...")
            console.print(table)
            
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to find intersections: {e}")
        raise typer.Exit(code=1)


from ai_manager import generate_suggestions, list_suggestions, review_suggestion

@ai_app.command("suggest")
def ai_suggest(
    source_id: str = typer.Argument(..., help="ID of the source"),
    code_id: int = typer.Argument(..., help="ID of the code"),
    provider: str = typer.Option("gemini", "--provider", "-p", help="AI provider to use (gemini, ollama)"),
    model: str = typer.Option(None, "--model", "-m", help="Model name (defaults depend on provider)")
):
    """Run AI semantic suggestion pass."""
    project_dir = get_current_project_dir()
    
    if model is None:
        if provider == "gemini":
            model = "flash"
        elif provider == "ollama":
            model = "deepseek-r1:14b"
            
    try:
        count = generate_suggestions(project_dir, source_id, code_id, provider=provider, model=model)
        log_command(project_dir, f"ai suggest {source_id} {code_id}", provider=provider, model=model)
        console.print(f"[bold green]Success:[/bold green] AI generated {count} suggestions for code {code_id} in source {source_id}. They are pending review.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to generate AI suggestions: {e}")
        raise typer.Exit(code=1)

@review_app.command("list")
def review_list(status: str = typer.Option("pending", help="Filter by status (pending, accepted, rejected)")):
    """List AI suggestions awaiting review."""
    project_dir = get_current_project_dir()
    try:
        suggestions = list_suggestions(project_dir, status=status)
        if not suggestions:
            console.print(f"No '{status}' suggestions found.")
            return
            
        table = Table(title=f"AI Suggestions ({status})")
        table.add_column("ID", style="cyan")
        table.add_column("Source", style="blue")
        table.add_column("Code ID", style="magenta")
        table.add_column("Span", style="green", max_width=50)
        table.add_column("Rationale", style="yellow", max_width=50)
        
        for s in suggestions:
            table.add_row(
                str(s["id"]), 
                str(s["source_id"]), 
                str(s["code_id"]), 
                s["span"][:100] + ("..." if len(s["span"]) > 100 else ""), 
                s["rationale"][:100] + ("..." if len(s["rationale"]) > 100 else "")
            )
        console.print(table)
        log_command(project_dir, f"review list {status}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to list suggestions: {e}")
        raise typer.Exit(code=1)

@review_app.command("accept")
def review_accept(
    suggestion_id: int = typer.Argument(..., help="ID of the suggestion to accept"),
    reason: str = typer.Option("", "--reason", "-r", help="Reason for accepting")
):
    """Accept an AI suggestion and convert it to a CodeAssignment."""
    project_dir = get_current_project_dir()
    try:
        review_suggestion(project_dir, suggestion_id, action="accept", reason=reason)
        log_command(project_dir, f"review accept {suggestion_id}")
        console.print(f"[bold green]Success:[/bold green] Accepted suggestion {suggestion_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to accept suggestion: {e}")
        raise typer.Exit(code=1)

@review_app.command("reject")
def review_reject(
    suggestion_id: int = typer.Argument(..., help="ID of the suggestion to reject"),
    reason: str = typer.Option("", "--reason", "-r", help="Reason for rejecting")
):
    """Reject an AI suggestion."""
    project_dir = get_current_project_dir()
    try:
        review_suggestion(project_dir, suggestion_id, action="reject", reason=reason)
        log_command(project_dir, f"review reject {suggestion_id}")
        console.print(f"[bold green]Success:[/bold green] Rejected suggestion {suggestion_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to reject suggestion: {e}")
        raise typer.Exit(code=1)

@ai_app.command("sense")
def ai_sense_cmd(
# ... existing code ...
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] AI sense failed: {e}")
        raise typer.Exit(code=1)

@ai_app.command("sense-list")
def ai_sense_list_cmd():
    """List all AI-identified theoretical intersections."""
    project_dir = get_current_project_dir()
    try:
        from intersection_manager import list_intersections
        intersections = list_intersections(project_dir)
        if not intersections:
            console.print("No intersections found.")
            return
            
        table = Table(title="AI-Sensed Theoretical Intersections")
        table.add_column("ID", style="cyan")
        table.add_column("Relationship", style="magenta")
        table.add_column("Codes", style="blue")
        table.add_column("Rationale", style="green")
        
        for i in intersections:
            table.add_row(
                str(i["id"]), 
                i["type"].upper(), 
                f"{i['code_a']} <-> {i['code_b']}", 
                i["rationale"][:100] + "..."
            )
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to list intersections: {e}")
        raise typer.Exit(code=1)

from search_manager import search_text, search_by_code, search_cross

@search_app.command("text")
def search_text_cmd(query: str = typer.Argument(..., help="Text query to search for")):
    """Search for a string across all canonical Markdown source files."""
    project_dir = get_current_project_dir()
    try:
        matches = search_text(project_dir, query)
        log_command(project_dir, f"search text '{query}'")
        
        if not matches:
            console.print(f"No matches found for '{query}'.")
            return
            
        table = Table(title=f"Search Results for '{query}'")
        table.add_column("Source ID", style="cyan")
        table.add_column("Snippet", style="green")
        table.add_column("File Path", style="blue")
        
        import re
        for m in matches:
            safe_snippet = m["snippet"].replace("[", "\\[").replace("]", "\\]")
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            highlighted = pattern.sub(lambda match: f"[bold red]{match.group(0)}[/bold red]", safe_snippet)
            table.add_row(m["source_id"], highlighted, m["file_path"])
            
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to search text: {e}")
        raise typer.Exit(code=1)

@search_app.command("code")
def search_code_cmd(code_id: int = typer.Argument(..., help="ID of the code to search for")):
    """Show all extracts assigned to a specific code."""
    project_dir = get_current_project_dir()
    try:
        results = search_by_code(project_dir, code_id)
        log_command(project_dir, f"search code {code_id}")
        
        if not results:
            console.print(f"No extracts found for code {code_id}.")
            return
            
        table = Table(title=f"Extracts for Code {code_id}")
        table.add_column("Assignment ID", style="cyan")
        table.add_column("Source ID", style="blue")
        table.add_column("Anchor", style="magenta")
        table.add_column("Text Span", style="green")
        
        for r in results:
            table.add_row(str(r["assignment_id"]), r["source_id"], r["anchor"], r["text_span"])
            
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to search code: {e}")
        raise typer.Exit(code=1)

@search_app.command("cross")
def search_cross_cmd(
    code_a: int = typer.Argument(..., help="ID of the first code"),
    code_b: int = typer.Argument(..., help="ID of the second code")
):
    """Identify sources where both codes appear."""
    project_dir = get_current_project_dir()
    try:
        results = search_cross(project_dir, code_a, code_b)
        log_command(project_dir, f"search cross {code_a} {code_b}")
        
        if not results:
            console.print(f"No sources found containing both codes {code_a} and {code_b}.")
            return
            
        table = Table(title=f"Cross-Search Results (Code {code_a} & Code {code_b})")
        table.add_column("Source ID", style="cyan")
        table.add_column("Source Type", style="blue")
        
        for r in results:
            table.add_row(r["source_id"], r["type"])
            
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to cross search: {e}")
        raise typer.Exit(code=1)

from memo_manager import create_memo, list_memos, delete_memo

@memo_app.command("create")
def memo_create_cmd(
    memo_type: str = typer.Argument(..., help="Type of memo (e.g., source, code, theme, general)"),
    text: str = typer.Argument(..., help="Content of the memo"),
    source_id: Optional[int] = typer.Option(None, help="Associated source ID"),
    extract_id: Optional[int] = typer.Option(None, help="Associated extract ID"),
    code_id: Optional[int] = typer.Option(None, help="Associated code ID"),
    theme_id: Optional[int] = typer.Option(None, help="Associated theme ID"),
    case_id: Optional[int] = typer.Option(None, help="Associated case ID")
):
    """Create a new memo."""
    project_dir = get_current_project_dir()
    try:
        memo_id = create_memo(
            project_dir, memo_type, text, 
            source_id=source_id, extract_id=extract_id, 
            code_id=code_id, theme_id=theme_id, case_id=case_id
        )
        log_command(project_dir, f"memo create {memo_type}", memo_id=memo_id)
        console.print(f"[bold green]Success:[/bold green] Created memo {memo_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to create memo: {e}")
        raise typer.Exit(code=1)

@memo_app.command("list")
def memo_list_cmd():
    """List all memos."""
    project_dir = get_current_project_dir()
    try:
        memos = list_memos(project_dir)
        log_command(project_dir, "memo list")
        if not memos:
            console.print("No memos found.")
            return
            
        table = Table(title="Memos")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Text", style="green")
        table.add_column("Created At", style="blue")
        
        for m in memos:
            text_preview = m["text"][:50] + ("..." if len(m["text"]) > 50 else "")
            table.add_row(str(m["memo_id"]), m["type"], text_preview, m["created_at"])
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to list memos: {e}")
        raise typer.Exit(code=1)

@memo_app.command("delete")
def memo_delete_cmd(memo_id: int = typer.Argument(..., help="ID of the memo to delete")):
    """Delete a memo."""
    project_dir = get_current_project_dir()
    try:
        delete_memo(project_dir, memo_id)
        log_command(project_dir, f"memo delete {memo_id}")
        console.print(f"[bold green]Success:[/bold green] Deleted memo {memo_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to delete memo: {e}")
        raise typer.Exit(code=1)

from case_manager import create_case, list_cases, delete_case, assign_case
from framework_manager import create_framework, add_dimension, list_frameworks, get_framework_details, delete_framework
from intersection_manager import add_intersection, list_intersections

@case_app.command("create")
def case_create_cmd(
    name: str = typer.Argument(..., help="Name of the case"),
    description: Optional[str] = typer.Option(None, help="Description of the case"),
    attributes: Optional[str] = typer.Option(None, help="JSON string of attributes")
):
    """Create a new case."""
    project_dir = get_current_project_dir()
    try:
        attrs = json.loads(attributes) if attributes else None
        case_id = create_case(project_dir, name, description=description, attributes=attrs)
        log_command(project_dir, f"case create {name}", case_id=case_id)
        console.print(f"[bold green]Success:[/bold green] Created case '{name}' with ID {case_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to create case: {e}")
        raise typer.Exit(code=1)

@case_app.command("list")
def case_list_cmd():
    """List all cases."""
    project_dir = get_current_project_dir()
    try:
        cases = list_cases(project_dir)
        log_command(project_dir, "case list")
        if not cases:
            console.print("No cases found.")
            return
            
        table = Table(title="Cases")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Description", style="green")
        table.add_column("Attributes", style="yellow")
        
        for c in cases:
            desc = c["description"] or ""
            attrs = json.dumps(c["attributes"]) if c["attributes"] else "{}"
            table.add_row(str(c["case_id"]), c["name"], desc, attrs)
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to list cases: {e}")
        raise typer.Exit(code=1)

@case_app.command("delete")
def case_delete_cmd(case_id: int = typer.Argument(..., help="ID of the case to delete")):
    """Delete a case."""
    project_dir = get_current_project_dir()
    try:
        delete_case(project_dir, case_id)
        log_command(project_dir, f"case delete {case_id}")
        console.print(f"[bold green]Success:[/bold green] Deleted case {case_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to delete case: {e}")
        raise typer.Exit(code=1)

@case_app.command("assign")
def case_assign_cmd(
    case_id: int = typer.Argument(..., help="ID of the case"),
    source_id: Optional[int] = typer.Option(None, "--source", "-s", help="ID of the source to assign"),
    extract_id: Optional[int] = typer.Option(None, "--extract", "-e", help="ID of the extract to assign")
):
    """Assign a source or extract to a case."""
    project_dir = get_current_project_dir()
    try:
        assign_case(project_dir, case_id, source_id=source_id, extract_id=extract_id)
        log_command(project_dir, f"case assign {case_id}", source_id=source_id, extract_id=extract_id)
        console.print(f"[bold green]Success:[/bold green] Assigned to case {case_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to assign case: {e}")
        raise typer.Exit(code=1)

@framework_app.command("create")
def framework_create_cmd(
    name: str = typer.Argument(..., help="Name of the framework"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Description")
):
    """Create a new theoretical framework."""
    project_dir = get_current_project_dir()
    try:
        f_id = create_framework(project_dir, name, description)
        log_command(project_dir, f"framework create {name}", framework_id=f_id)
        console.print(f"[bold green]Success:[/bold green] Created framework '{name}' with ID {f_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to create framework: {e}")
        raise typer.Exit(code=1)

@framework_app.command("add-dim")
def framework_add_dim_cmd(
    framework_id: int = typer.Argument(..., help="ID of the framework"),
    name: str = typer.Argument(..., help="Name of the dimension"),
    definition: str = typer.Argument(..., help="Definition of the dimension"),
    code_id: Optional[int] = typer.Option(None, "--code", "-c", help="Mapped code ID")
):
    """Add a dimension to a framework."""
    project_dir = get_current_project_dir()
    try:
        d_id = add_dimension(project_dir, framework_id, name, definition, code_id)
        log_command(project_dir, f"framework add-dim {framework_id} {name}", dimension_id=d_id)
        console.print(f"[bold green]Success:[/bold green] Added dimension '{name}' with ID {d_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to add dimension: {e}")
        raise typer.Exit(code=1)

@framework_app.command("list")
def framework_list_cmd():
    """List all theoretical frameworks."""
    project_dir = get_current_project_dir()
    try:
        frameworks = list_frameworks(project_dir)
        table = Table(title="Theoretical Frameworks")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Dimensions", style="blue")
        table.add_column("Description", style="green")
        
        for f in frameworks:
            table.add_row(str(f["id"]), f["name"], str(f["dimensions_count"]), f["description"] or "")
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to list frameworks: {e}")
        raise typer.Exit(code=1)

from map_manager import (
    create_cluster, list_clusters, delete_cluster, assign_code_to_cluster, unassign_code_from_cluster,
    create_theme, list_themes, delete_theme, assign_code_to_theme, unassign_code_from_theme,
    assign_cluster_to_theme, unassign_cluster_from_theme
)

@cluster_app.command("create")
def cluster_create_cmd(
    name: str = typer.Argument(..., help="Name of the cluster"),
    description: Optional[str] = typer.Option(None, help="Description of the cluster")
):
    """Create a new cluster."""
    project_dir = get_current_project_dir()
    try:
        cluster_id = create_cluster(project_dir, name, description)
        log_command(project_dir, f"map cluster create {name}", cluster_id=cluster_id)
        console.print(f"[bold green]Success:[/bold green] Created cluster '{name}' with ID {cluster_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to create cluster: {e}")
        raise typer.Exit(code=1)

@cluster_app.command("list")
def cluster_list_cmd():
    """List all clusters."""
    project_dir = get_current_project_dir()
    try:
        clusters = list_clusters(project_dir)
        log_command(project_dir, "map cluster list")
        if not clusters:
            console.print("No clusters found.")
            return
            
        table = Table(title="Clusters")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Description", style="green")
        
        for c in clusters:
            table.add_row(str(c["cluster_id"]), c["name"], c["description"] or "")
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to list clusters: {e}")
        raise typer.Exit(code=1)

@cluster_app.command("delete")
def cluster_delete_cmd(cluster_id: int = typer.Argument(..., help="ID of the cluster to delete")):
    """Delete a cluster."""
    project_dir = get_current_project_dir()
    try:
        delete_cluster(project_dir, cluster_id)
        log_command(project_dir, f"map cluster delete {cluster_id}")
        console.print(f"[bold green]Success:[/bold green] Deleted cluster {cluster_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to delete cluster: {e}")
        raise typer.Exit(code=1)

@cluster_app.command("assign")
def cluster_assign_cmd(
    cluster_id: int = typer.Argument(..., help="ID of the cluster"),
    code_id: int = typer.Argument(..., help="ID of the code to assign")
):
    """Assign a code to a cluster."""
    project_dir = get_current_project_dir()
    try:
        assign_code_to_cluster(project_dir, code_id, cluster_id)
        log_command(project_dir, f"map cluster assign {cluster_id} {code_id}")
        console.print(f"[bold green]Success:[/bold green] Assigned code {code_id} to cluster {cluster_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to assign code: {e}")
        raise typer.Exit(code=1)

@cluster_app.command("unassign")
def cluster_unassign_cmd(
    cluster_id: int = typer.Argument(..., help="ID of the cluster"),
    code_id: int = typer.Argument(..., help="ID of the code to unassign")
):
    """Unassign a code from a cluster."""
    project_dir = get_current_project_dir()
    try:
        unassign_code_from_cluster(project_dir, code_id, cluster_id)
        log_command(project_dir, f"map cluster unassign {cluster_id} {code_id}")
        console.print(f"[bold green]Success:[/bold green] Unassigned code {code_id} from cluster {cluster_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to unassign code: {e}")
        raise typer.Exit(code=1)

@theme_app.command("create")
def theme_create_cmd(
    name: str = typer.Argument(..., help="Name of the theme"),
    description: Optional[str] = typer.Option(None, help="Description of the theme"),
    parent_id: Optional[int] = typer.Option(None, help="ID of the parent theme")
):
    """Create a new theme."""
    project_dir = get_current_project_dir()
    try:
        theme_id = create_theme(project_dir, name, description, parent_theme_id=parent_id)
        log_command(project_dir, f"map theme create {name}", theme_id=theme_id)
        console.print(f"[bold green]Success:[/bold green] Created theme '{name}' with ID {theme_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to create theme: {e}")
        raise typer.Exit(code=1)

@theme_app.command("list")
def theme_list_cmd():
    """List all themes."""
    project_dir = get_current_project_dir()
    try:
        themes = list_themes(project_dir)
        log_command(project_dir, "map theme list")
        if not themes:
            console.print("No themes found.")
            return
            
        table = Table(title="Themes")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Description", style="green")
        table.add_column("Parent ID", style="blue")
        
        for t in themes:
            table.add_row(str(t["theme_id"]), t["name"], t["description"] or "", str(t["parent_theme_id"]) if t["parent_theme_id"] else "")
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to list themes: {e}")
        raise typer.Exit(code=1)

@theme_app.command("delete")
def theme_delete_cmd(theme_id: int = typer.Argument(..., help="ID of the theme to delete")):
    """Delete a theme."""
    project_dir = get_current_project_dir()
    try:
        delete_theme(project_dir, theme_id)
        log_command(project_dir, f"map theme delete {theme_id}")
        console.print(f"[bold green]Success:[/bold green] Deleted theme {theme_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to delete theme: {e}")
        raise typer.Exit(code=1)


@theme_app.command("assign-code")
def theme_assign_code_cmd(
    theme_id: int = typer.Argument(..., help="ID of the theme"),
    code_id: int = typer.Argument(..., help="ID of the code to assign")
):
    """Assign a code to a theme."""
    project_dir = get_current_project_dir()
    try:
        assign_code_to_theme(project_dir, code_id, theme_id)
        log_command(project_dir, f"map theme assign-code {theme_id} {code_id}")
        console.print(f"[bold green]Success:[/bold green] Assigned code {code_id} to theme {theme_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to assign code to theme: {e}")
        raise typer.Exit(code=1)

@theme_app.command("unassign-code")
def theme_unassign_code_cmd(
    theme_id: int = typer.Argument(..., help="ID of the theme"),
    code_id: int = typer.Argument(..., help="ID of the code to unassign")
):
    """Unassign a code from a theme."""
    project_dir = get_current_project_dir()
    try:
        unassign_code_from_theme(project_dir, code_id, theme_id)
        log_command(project_dir, f"map theme unassign-code {theme_id} {code_id}")
        console.print(f"[bold green]Success:[/bold green] Unassigned code {code_id} from theme {theme_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to unassign code from theme: {e}")
        raise typer.Exit(code=1)

@theme_app.command("assign-cluster")
def theme_assign_cluster_cmd(
    theme_id: int = typer.Argument(..., help="ID of the theme"),
    cluster_id: int = typer.Argument(..., help="ID of the cluster to assign")
):
    """Assign a cluster to a theme."""
    project_dir = get_current_project_dir()
    try:
        assign_cluster_to_theme(project_dir, cluster_id, theme_id)
        log_command(project_dir, f"map theme assign-cluster {theme_id} {cluster_id}")
        console.print(f"[bold green]Success:[/bold green] Assigned cluster {cluster_id} to theme {theme_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to assign cluster to theme: {e}")
        raise typer.Exit(code=1)

@theme_app.command("unassign-cluster")
def theme_unassign_cluster_cmd(
    theme_id: int = typer.Argument(..., help="ID of the theme"),
    cluster_id: int = typer.Argument(..., help="ID of the cluster to unassign")
):
    """Unassign a cluster from a theme."""
    project_dir = get_current_project_dir()
    try:
        unassign_cluster_from_theme(project_dir, cluster_id, theme_id)
        log_command(project_dir, f"map theme unassign-cluster {theme_id} {cluster_id}")
        console.print(f"[bold green]Success:[/bold green] Unassigned cluster {cluster_id} from theme {theme_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to unassign cluster from theme: {e}")
        raise typer.Exit(code=1)

from gut_manager import tag_extract, list_tags

@gut_app.command("tag")
def gut_tag_cmd(
    extract_id: int = typer.Argument(..., help="ID of the extract to tag"),
    proposed_code_id: Optional[int] = typer.Option(None, help="Proposed code ID"),
    confidence: str = typer.Option(None, help="Confidence level"),
    trigger_phrases: str = typer.Option(None, help="Trigger phrases"),
    rationale: str = typer.Option(None, help="Rationale"),
    linked_rule: str = typer.Option(None, help="Linked rule"),
    ladder_position: str = typer.Option(None, help="Ladder position"),
    alternatives: str = typer.Option(None, help="Alternatives considered")
):
    """Tag an extract with a JudgementNote."""
    project_dir = get_current_project_dir()
    try:
        note_id = tag_extract(
            project_dir, extract_id, proposed_code_id, confidence,
            trigger_phrases, rationale, linked_rule, ladder_position, alternatives
        )
        log_command(project_dir, f"gut tag {extract_id}", note_id=note_id)
        console.print(f"[bold green]Success:[/bold green] Tagged extract {extract_id} with JudgementNote {note_id}.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to tag extract: {e}")
        raise typer.Exit(code=1)

@gut_app.command("list")
def gut_list_cmd(
    extract_id: Optional[int] = typer.Option(None, help="Filter by extract ID")
):
    """List JudgementNotes (Gut tags)."""
    project_dir = get_current_project_dir()
    try:
        notes = list_tags(project_dir, extract_id)
        log_command(project_dir, f"gut list", extract_id=extract_id)
        if not notes:
            console.print("No gut tags found.")
            return
            
        table = Table(title="JudgementNotes")
        table.add_column("Note ID", style="cyan")
        table.add_column("Extract ID", style="blue")
        table.add_column("Code ID", style="magenta")
        table.add_column("Confidence", style="yellow")
        table.add_column("Rationale", style="green")
        
        for n in notes:
            rat = n["rationale"] or ""
            rat_preview = rat[:30] + ("..." if len(rat) > 30 else "")
            table.add_row(
                str(n["note_id"]), str(n["extract_id"]), 
                str(n["proposed_code_id"]) if n["proposed_code_id"] else "", 
                n["confidence"] or "", rat_preview
            )
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to list gut tags: {e}")
        raise typer.Exit(code=1)

from report_manager import generate_codebook_report, generate_extracts_report, generate_matrix_report, generate_theme_pack
from advanced_matrix_manager import build_advanced_matrix
from gpviz_export_manager import export_gp_viz
from ai_sense_manager import perform_ai_sense
from narrative_manager import synthesize_evolution

@report_app.command("codebook")
def report_codebook_cmd(
    format: str = typer.Option("default", "--format", "-f", help="Output format: default, md, csv, xlsx, docx, pdf")
):
    """Generate the codebook report."""
    project_dir = get_current_project_dir()
    try:
        paths = generate_codebook_report(project_dir, format=format)
        log_command(project_dir, f"report codebook --format {format}")
        for path in paths:
            console.print(f"[bold green]Success:[/bold green] Codebook report generated at '{path}'.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to generate codebook report: {e}")
        raise typer.Exit(code=1)

@report_app.command("extracts")
def report_extracts_cmd(
    format: str = typer.Option("default", "--format", "-f", help="Output format: default, md, csv, xlsx, docx, pdf")
):
    """Generate the extracts report."""
    project_dir = get_current_project_dir()
    try:
        paths = generate_extracts_report(project_dir, format=format)
        log_command(project_dir, f"report extracts --format {format}")
        for path in paths:
            console.print(f"[bold green]Success:[/bold green] Extracts report generated at '{path}'.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to generate extracts report: {e}")
        raise typer.Exit(code=1)

@report_app.command("matrix")
def report_matrix_cmd(
    format: str = typer.Option("default", "--format", "-f", help="Output format: default, md, csv, xlsx, docx, pdf"),
    advanced: bool = typer.Option(False, "--advanced", help="Generate advanced matrix with density/breadth"),
    x_axis: str = typer.Option("case", "--x-axis", help="X-axis category (theme, cluster, case, case_attr:<key>)"),
    y_axis: str = typer.Option("theme", "--y-axis", help="Y-axis category (theme, cluster, case, case_attr:<key>)")
):
    """Generate the matrix analytics report."""
    project_dir = get_current_project_dir()
    try:
        if advanced:
            matrix_data = build_advanced_matrix(project_dir, x_axis, y_axis)
            # Render to Rich table for CLI
            table = Table(title=f"Advanced Matrix: {x_axis} vs {y_axis}")
            table.add_column(f"{y_axis} \\ {x_axis}", style="cyan")
            
            x_labels = matrix_data["x_labels"]
            for x in x_labels:
                table.add_column(x, justify="center")
            
            for y_label in matrix_data["y_labels"]:
                row = [y_label]
                for x_label in x_labels:
                    cell = matrix_data["matrix"][x_label].get(y_label, {"density": 0, "breadth": 0})
                    row.append(f"D:{cell['density']}\nB:{cell['breadth']}")
                table.add_row(*row)
            
            console.print(table)
            log_command(project_dir, f"report matrix --advanced --x-axis {x_axis} --y-axis {y_axis}")
        else:
            paths = generate_matrix_report(project_dir, format=format)
            log_command(project_dir, f"report matrix --format {format}")
            for path in paths:
                console.print(f"[bold green]Success:[/bold green] Matrix report generated at '{path}'.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to generate matrix report: {e}")
        raise typer.Exit(code=1)

@report_app.command("theme-pack")
def report_theme_pack_cmd(
    theme_id: int = typer.Argument(..., help="ID of the theme for the pack"),
    format: str = typer.Option("default", "--format", "-f", help="Output format: default, md, csv, xlsx, docx, pdf")
):
    """Generate a theme evidence pack."""
    project_dir = get_current_project_dir()
    try:
        paths = generate_theme_pack(project_dir, theme_id, format=format)
        log_command(project_dir, f"report theme-pack {theme_id} --format {format}")
        for path in paths:
            console.print(f"[bold green]Success:[/bold green] Theme evidence pack generated at '{path}'.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to generate theme evidence pack: {e}")
        raise typer.Exit(code=1)

@report_app.command("evolution")
def report_evolution_cmd(
    start_date: Optional[str] = typer.Option(None, "--start", help="Start date (YYYY-MM-DD)"),
):
    """Generate a narrative audit trail of how the theory evolved."""
    project_dir = get_current_project_dir()
    try:
        date_obj = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        
        with console.status("[bold green]Synthesizing evolution narrative (this may take a minute)..."):
            narrative = synthesize_evolution(project_dir, date_obj)
            
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = project_dir / "reports" / f"evolution_{timestamp}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(narrative)
            
        log_command(project_dir, "report evolution", start_date=start_date)
        console.print(f"[bold green]Success:[/bold green] Evolution report generated at '{report_path}'.")
        console.print("\n--- Narrative Preview ---\n")
        console.print(narrative[:1000] + ("..." if len(narrative) > 1000 else ""))
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to generate evolution report: {e}")
        raise typer.Exit(code=1)

@export_app.command("gp-viz")
def export_gpviz_cmd():
    """Export project as a semantic landscape for GP-Viz visualization."""
    project_dir = get_current_project_dir()
    try:
        output_path = export_gp_viz(str(project_dir))
        log_command(project_dir, "export gp-viz", output=output_path)
        console.print(f"[bold green]Success:[/bold green] Semantic landscape exported to '{output_path}'.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to export GP-Viz data: {e}")
        raise typer.Exit(code=1)

from snapshot_manager import create_snapshot, restore_snapshot

@snapshot_app.command("create")
def snapshot_create_cmd(
    description: str = typer.Option("", help="Optional description of the snapshot")
):
    """Create a versioned bundle of the current database and canonical files."""
    project_dir = get_current_project_dir()
    try:
        snapshot_name = create_snapshot(project_dir, description)
        log_command(project_dir, f"snapshot create '{description}'")
        console.print(f"[bold green]Success:[/bold green] Snapshot '{snapshot_name}' created.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to create snapshot: {e}")
        raise typer.Exit(code=1)

@snapshot_app.command("restore")
def snapshot_restore_cmd(
    snapshot_name: str = typer.Argument(..., help="Name of the snapshot zip file to restore")
):
    """Restore a specific snapshot, replacing current DB and canonical files."""
    project_dir = get_current_project_dir()
    try:
        backup_path = restore_snapshot(project_dir, snapshot_name)
        log_command(project_dir, f"snapshot restore {snapshot_name}")
        console.print(f"[bold green]Success:[/bold green] Snapshot '{snapshot_name}' restored.")
        console.print(f"A backup of the previous state was saved at: {backup_path}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to restore snapshot: {e}")
        raise typer.Exit(code=1)

from source_manager import check_integrity

@project_app.command("check")
def project_check_cmd():
    """Check the integrity of the project database and files."""
    project_dir = get_current_project_dir()
    try:
        issues = check_integrity(project_dir)
        log_command(project_dir, "project check")
        if issues:
            console.print("[bold red]Integrity issues found:[/bold red]")
            for issue in issues:
                console.print(f"- {issue}")
            raise typer.Exit(code=1)
        else:
            console.print("[bold green]Success:[/bold green] No integrity issues found. Project is healthy.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to check project integrity: {e}")
        raise typer.Exit(code=1)

from models import AuditLog

@project_app.command("finalize")
def project_finalize_cmd():
    """Finalize the project and log the event."""
    project_dir = get_current_project_dir()
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        db_path = project_dir / "db" / "tt.sqlite"
        engine = create_engine(f"sqlite:///{db_path}")
        with Session(engine) as session:
            audit_log = AuditLog(
                action="project_finalized",
                entity_type="Project",
                entity_id="1",
                user_id="cli_user",
                details={"phase": "Phase 5 complete"}
            )
            session.add(audit_log)
            session.commit()
            
        log_command(project_dir, "project finalize")
        console.print("[bold green]Success:[/bold green] Project finalized. Event recorded in AuditLog.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to finalize project: {e}")
        raise typer.Exit(code=1)

from irr_manager import generate_irr_sample, calculate_cohen_kappa

@irr_app.command("sample")
def irr_sample_cmd(
    source_id: int = typer.Argument(..., help="ID of the source to sample"),
    percent: int = typer.Option(20, "--percent", "-p", help="Percentage of extracts to sample")
):
    """Generate a random sample of extracts for blind-coding."""
    project_dir = get_current_project_dir()
    try:
        sample_ids = generate_irr_sample(project_dir, source_id, percent)
        log_command(project_dir, f"irr sample {source_id}", percent=percent, sample_count=len(sample_ids))
        
        if not sample_ids:
            console.print(f"[yellow]No extracts found for source {source_id}.[/yellow]")
            return
            
        console.print(f"[bold green]Success:[/bold green] Generated IRR sample of {len(sample_ids)} extracts (top {percent}%).")
        table = Table(title=f"Sampled Extract IDs for Source {source_id}")
        table.add_column("Extract ID", style="cyan")
        for eid in sample_ids:
            table.add_row(str(eid))
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to generate IRR sample: {e}")
        raise typer.Exit(code=1)

@irr_app.command("score")
def irr_score_cmd(
    coder_a: str = typer.Argument(..., help="ID of the first coder"),
    coder_b: str = typer.Argument(..., help="ID of the second coder")
):
    """Calculate and display Cohen's Kappa score for two coders."""
    project_dir = get_current_project_dir()
    try:
        kappa = calculate_cohen_kappa(project_dir, coder_a, coder_b)
        log_command(project_dir, f"irr score {coder_a} {coder_b}", kappa=kappa)
        
        table = Table(title="Inter-Rater Reliability (Cohen's Kappa)")
        table.add_column("Coder A", style="blue")
        table.add_column("Coder B", style="magenta")
        table.add_column("Kappa Score", style="green")
        
        table.add_row(coder_a, coder_b, f"{kappa:.4f}")
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to calculate IRR score: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
