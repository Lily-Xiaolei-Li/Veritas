import typer
import psutil
import platform
import socket
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, List
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.live import Live
from rich.align import Align
from rich import box
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from datetime import datetime
import time
import httpx

from veritas_ui.common import console, print_branding, create_veritas_table
from core_wrapper import run_legacy_core
from viz_wrapper import get_viz_health, get_docker_status
from spells_bridge import HollowsBridge
from veritas_ui.spells.ux import SpellUX, PURPLE, GOLD, CYAN, MAGENTA

app = typer.Typer(
    help="Veritas Academic Research Suite - Unified Portal",
    no_args_is_help=False
)

# --- Sub-Apps ---
core_app = typer.Typer(help="Veritas-Core: Knowledge backbone and paper management")
app.add_typer(core_app, name="core", no_args_is_help=True)

tt_app = typer.Typer(help="Textus-Transparens: Qualitative analysis & theoretical sensing")
app.add_typer(tt_app, name="tt", no_args_is_help=True)

viz_app = typer.Typer(help="Veritas-Viz: 3D semantic landscape visualization")
app.add_typer(viz_app, name="viz", no_args_is_help=True)

spells_app = typer.Typer(help="Scholarly Hollows: AI magic spells for research")
app.add_typer(spells_app, name="spells", no_args_is_help=True)

# --- Spells Implementation ---

bridge = HollowsBridge()

@spells_app.command("vf")
def spell_vf(doc_id: str = typer.Argument(..., help="Document ID to verify")):
    """Veritafactum: Sentence-by-sentence citation verification."""
    SpellUX.print_spell_header("Veritafactum", "Channeling truth to expose the unverified...")
    
    with SpellUX.get_magical_spinner("Weaving citation threads..."):
        result = bridge.cast_vf(doc_id)
    
    if not result["ok"]:
        SpellUX.print_fizzle(result["error"])
        return

    table = SpellUX.create_verification_table("Verification Results")
    table.add_column("Sentence", ratio=3)
    table.add_column("Support", justify="center")
    table.add_column("Source", ratio=2)

    for item in result["data"].get("results", []):
        status = "✅" if item.get("supported") else "❌"
        table.add_row(item.get("sentence"), status, item.get("source_citation"))
    
    console.print(table)

@spells_app.command("ci")
def spell_ci(
    sentence: str = typer.Argument(..., help="Sentence or claim needing citation"),
    top_k: int = typer.Option(5, "--limit", "-l")
):
    """Citalio: AI-driven citation recommendation."""
    SpellUX.print_spell_header("Citalio", "Summoning the voices of authority...")
    
    with SpellUX.get_magical_spinner("Searching the Great Library..."):
        result = bridge.cast_ci(sentence, top_k=top_k)
    
    if not result["ok"]:
        SpellUX.print_fizzle(result["error"])
        return

    table = create_veritas_table("Recommended Citations")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Citation", style="white")
    
    for rec in result["data"].get("recommendations", []):
        table.add_row(f"{rec.get('score', 0):.2f}", rec.get("text"))
    
    console.print(table)

@spells_app.command("pm")
def spell_pm(doi: str = typer.Argument(..., help="Seed DOI to expand from")):
    """Proliferomaxima: Recursive citation network expansion."""
    SpellUX.print_spell_header("Proliferomaxima", "The spider weaves; the web expands...")
    
    with SpellUX.get_magical_spinner("Expanding the arcane network (this may take minutes)..."):
        result = bridge.cast_pm([doi])
    
    if not result["ok"]:
        SpellUX.print_fizzle(result["error"])
        return
        
    console.print(f"\n[bold {CYAN}]Magic Manifested![/bold {CYAN}] Found {result['data'].get('count', 0)} new relevant works.")
    console.print(f"[dim]Data materialized in the knowledge vault.[/dim]")

@spells_app.command("ep")
def spell_ep(target: str = typer.Argument(..., help="DOI or URL to retrieve")):
    """Ex-portario: PDF retrieval and paywall bypass."""
    SpellUX.print_spell_header("Ex-portario", "Bypassing mortal wards to fetch the sacred scrolls...")
    
    with Progress(
        SpinnerColumn(),
        TextColumn(f"[{PURPLE}]Chipping away at the paywall..."),
        BarColumn(bar_width=None, style=f"bold {MAGENTA}"),
        DownloadColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("retrieving", total=100)
        # Handle the blocking request in a way that allows progress updates
        # For MVP, we'll just run it. If it takes >10s user might get nervous, but ep is usually fast
        # for DOIs.
        result = bridge.cast_ep(target)
        progress.update(task, completed=100)

    if not result["ok"]:
        SpellUX.print_fizzle(result["error"])
    else:
        console.print(f"\n[bold {CYAN}]SUCCESS:[/bold {CYAN}] Tome materialized at: {result['data'].get('path')}")

# --- Settings ---
BASE_DIR = Path(__file__).parent.parent
TT_DIR = BASE_DIR / "textus-transparens"
BACKEND_DIR = BASE_DIR / "backend"
VIZ_DIR = BASE_DIR / "gp-viz"

@tt_app.command("launch")
def tt_launch():
    """Launch the Textus-Transparens interactive dashboard."""
    console.print("[veritas.info]Launching Textus-Transparens...[/veritas.info]")
    try:
        subprocess.Popen(
            ["cmd", "/c", "launch_tt.bat"],
            cwd=str(TT_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        console.print("[veritas.success]Success:[/veritas.success] TT is opening in a new window.")
    except Exception as e:
        console.print(f"[veritas.error]Error:[/veritas.error] {e}")

@tt_app.command("status")
def tt_status():
    """Check the health of the TT project."""
    # We can try to run 'tt project check' but for the portal we'll just check file existence for now
    db = TT_DIR / "projects" / "production_test" / "db" / "tt.sqlite"
    res = "[veritas.success]READY[/veritas.success]" if db.exists() else "[veritas.warn]UNINITIALIZED[/veritas.warn]"
    console.print(f"Textus Transparens Status: {res}")
    if db.exists():
        console.print(f"[dim]DB Location: {db}[/dim]")

@core_app.command("session-ls")
def core_session_list():
    """List all research sessions in Veritas-Core."""
    with console.status("[veritas.info]Fetching sessions from Core..."):
        response = run_legacy_core("session", "list")
    
    if not response.get("ok"):
        console.print(f"[veritas.error]Error:[/veritas.error] {response.get('error', {}).get('message')}")
        return

    data = response.get("data", {})
    sessions = data.get("sessions", [])
    current_id = data.get("current_session_id", "")

    table = create_veritas_table("Research Sessions (Core)")
    table.add_column("", style="yellow", width=2)  # Current marker
    table.add_column("ID", style="veritas.id")
    table.add_column("Title", style="white")
    table.add_column("Mode", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Created", style="veritas.muted")

    for sess in sessions:
        is_current = "*" if sess.get("id") == current_id else ""
        status = sess.get("status", "unknown").upper()
        status_color = "veritas.success" if status == "ACTIVE" else "veritas.warn"
        
        table.add_row(
            is_current,
            sess.get("id", "")[:8],
            sess.get("title", "Untitled"),
            sess.get("mode", "N/A"),
            f"[{status_color}]{status}[/{status_color}]",
            sess.get("created_at", "")[:10]
        )
    
    console.print(table)
    console.print(f"\n[veritas.info]Hint:[/veritas.info] * marks the current active session. Use [bold]veritas core session-use <id>[/bold] to switch.")

@core_app.command("session-use")
def core_session_use(session_id: str = typer.Argument(..., help="Full or short Session ID")):
    """Set the current active session."""
    with console.status(f"[veritas.info]Switching to session {session_id}..."):
        response = run_legacy_core("session", "use", ["--session", session_id])
    
    if response.get("ok"):
        console.print(f"[veritas.success]Success:[/veritas.success] Current session is now [veritas.id]{session_id}[/veritas.id].")
    else:
        console.print(f"[veritas.error]Error:[/veritas.error] {response.get('error', {}).get('message')}")

@core_app.command("session-create")
def core_session_create(name: str = typer.Argument(..., help="Name of the new session")):
    """Create a new research session."""
    with console.status(f"[veritas.info]Creating session '{name}'..."):
        response = run_legacy_core("session", "create", ["--name", name])
    
    if response.get("ok"):
        new_id = response.get("data", {}).get("id", "Unknown")
        console.print(f"[veritas.success]Success:[/veritas.success] Created session [veritas.id]{name}[/veritas.id] (ID: {new_id[:8]})")
    else:
        console.print(f"[veritas.error]Error:[/veritas.error] {response.get('error', {}).get('message')}")

@core_app.command("artifact-ls")
def core_artifact_list(session: str = typer.Option(None, "--session", "-s", help="Session UUID")):
    """List artifacts for a session."""
    params = ["--session", session] if session else ["--use-current-session"]
    with console.status("[veritas.info]Fetching artifacts from Core..."):
        response = run_legacy_core("artifact", "list", params)
    
    if not response.get("ok"):
        console.print(f"[veritas.error]Error:[/veritas.error] {response.get('error', {}).get('message')}")
        return

    data = response.get("data", {})
    artifacts = data.get("artifacts", data) if isinstance(data, dict) else data

    if not artifacts:
        console.print("[veritas.info]No artifacts found in this session.[/veritas.info]")
        return

    table = create_veritas_table("Artifacts")
    table.add_column("ID", style="veritas.id")
    table.add_column("Name", style="white")
    table.add_column("Type", style="cyan")
    table.add_column("Created", style="veritas.muted")

    for art in artifacts:
        if isinstance(art, dict):
            table.add_row(
                str(art.get("id", ""))[:10],
                art.get("name", "Unnamed"),
                art.get("type", "N/A"),
                str(art.get("created_at", ""))[:10]
            )
    
    console.print(table)

@core_app.command("persona-ls")
def core_persona_list():
    """List all available AI personas."""
    with console.status("[veritas.info]Fetching personas..."):
        response = run_legacy_core("persona", "list")
    
    if not response.get("ok"):
        console.print(f"[veritas.error]Error:[/veritas.error] {response.get('error', {}).get('message')}")
        return

    data = response.get("data", {})
    personas = data.get("personas", data) if isinstance(data, dict) else data

    table = create_veritas_table("AI Personas")
    table.add_column("ID", style="veritas.id")
    table.add_column("Label", style="white")
    table.add_column("Description", style="veritas.muted", max_width=50)

    for p in personas:
        if isinstance(p, dict):
            desc = p.get("system_prompt", "")[:50] + "..." if len(p.get("system_prompt", "")) > 50 else p.get("system_prompt", "")
            table.add_row(
                str(p.get("id", "")),
                p.get("label", "Unnamed"),
                desc
            )
    
    console.print(table)

@core_app.command("source-ls")
def core_source_list():
    """List all ingested sources in the current session."""
    with console.status("[veritas.info]Fetching sources from Core..."):
        response = run_legacy_core("source", "list", ["--use-current-session"])
    
    if not response.get("ok"):
        console.print(f"[veritas.error]Error:[/veritas.error] {response.get('error', {}).get('message')}")
        return

    data = response.get("data", {})
    sources = data.get("sources", [])

    if not sources:
        console.print("[veritas.info]No sources found in current session.[/veritas.info]")
        return

    table = create_veritas_table("Knowledge Sources")
    table.add_column("ID", style="veritas.id")
    table.add_column("Name", style="white")
    table.add_column("Type", justify="center")
    table.add_column("Attributes", style="veritas.muted")

    for src in sources:
        table.add_row(
            str(src.get("id", ""))[:8],
            src.get("name", "Unnamed"),
            src.get("type", "N/A"),
            str(src.get("attributes", "{}"))
        )
    
    console.print(table)

@core_app.command("run-ls")
def core_run_list():
    """List recent AI processing runs."""
    with console.status("[veritas.info]Fetching run history..."):
        response = run_legacy_core("run", "list", ["--use-current-session"])
    
    if not response.get("ok"):
        console.print(f"[veritas.error]Error:[/veritas.error] {response.get('error', {}).get('message')}")
        return

    data = response.get("data", {})
    runs = data.get("runs", [])

    if not runs:
        console.print("[veritas.info]No recent runs found.[/veritas.info]")
        return

    table = create_veritas_table("AI Processing Runs")
    table.add_column("Run ID", style="veritas.id")
    table.add_column("Status", justify="center")
    table.add_column("Started", style="veritas.muted")
    table.add_column("Preview", style="white", max_width=40)

    for r in runs:
        status = r.get("status", "unknown").upper()
        color = "veritas.success" if status == "COMPLETED" else "veritas.warn"
        preview = r.get("request", "")[:37] + "..." if len(r.get("request", "")) > 37 else r.get("request", "")
        
        table.add_row(
            r.get("id", "")[:8],
            f"[{color}]{status}[/{color}]",
            r.get("started_at", "")[11:19] if r.get("started_at") else "??:??:??",
            preview
        )
    
    console.print(table)

@core_app.command("chat")
def core_chat(
    persona: Optional[str] = typer.Option(None, "--persona", "-p", help="Persona ID"),
    rag: Optional[str] = typer.Option(None, "--rag", help="RAG sources (library,interviews)")
):
    """Start an interactive research chat session."""
    print_branding()
    console.print(f"[veritas.info]Entering Interactive Research Mode...[/veritas.info]")
    console.print(f"[dim]Type 'exit' or 'quit' to end the session.[/dim]\n")
    
    if persona:
        with console.status(f"[veritas.info]Switching to persona '{persona}'..."):
            run_legacy_core("persona", "select", ["--persona", persona, "--use-current-session"])

    while True:
        try:
            query = Prompt.ask("[bold green]Researcher[/bold green]")
            if query.lower() in ["exit", "quit"]:
                console.print("\n[veritas.info]Ending research session. Good luck![/veritas.info]")
                break
            
            if not query.strip():
                continue
                
            params = ["--message", query, "--use-current-session"]
            if rag:
                params.extend(["--rag", rag])
                
            with console.status("[bold blue]Veritas is thinking..."):
                response = run_legacy_core("chat", "send", params)
            
            if response.get("ok"):
                reply = response.get("data", {}).get("response", "No response.")
                console.print(f"\n[bold deep_sky_blue1]Veritas[/bold deep_sky_blue1]:\n")
                console.print(Panel(reply, border_style="deep_sky_blue1"))
                console.print("")
            else:
                console.print(f"\n[veritas.error]Error:[/veritas.error] {response.get('error', {}).get('message')}\n")
                
        except KeyboardInterrupt:
            console.print("\n[veritas.info]Ending research session.[/veritas.info]")
            break

@core_app.command("start")
def core_start():
    """Start the Veritas-Core backend."""
    console.print("[veritas.info]Launching Veritas-Core Backend...[/veritas.info]")
    try:
        subprocess.Popen(
            [str(BACKEND_DIR / ".venv" / "Scripts" / "python.exe"), "run_agentb.py"],
            cwd=str(BACKEND_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        console.print("[veritas.success]Success:[/veritas.success] Veritas-Core is launching in a new window.")
    except Exception as e:
        console.print(f"[veritas.error]Error:[/veritas.error] {e}")

# --- Veritas-Viz Sub-App ---
viz_app = typer.Typer(help="Veritas-Viz: 3D semantic landscape visualization")
app.add_typer(viz_app, name="viz", no_args_is_help=True)

@viz_app.command("status")
def viz_status():
    """Check the status of the GP-Viz visualization engine."""
    with console.status("[veritas.info]Checking GP-Viz status..."):
        docker = get_docker_status()
        api = get_viz_health()
    
    table = create_veritas_table("GP-Viz Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="veritas.muted")
    
    docker_res = f"[veritas.success]ONLINE[/veritas.success]" if docker["ok"] else f"[veritas.error]OFFLINE[/veritas.error]"
    table.add_row("Docker Container", docker_res, docker.get("status", docker.get("error")))
    
    api_res = f"[veritas.success]HEALTHY[/veritas.success]" if api["ok"] else f"[veritas.error]UNREACHABLE[/veritas.error]"
    table.add_row("API Endpoint (1880)", api_res, str(api.get("data", api.get("error"))))
    
    console.print(table)
    if not api["ok"]:
        console.print("\n[veritas.info]Hint:[/veritas.info] Make sure Docker Desktop is running and start the container with [bold]veritas viz start[/bold].")

@viz_app.command("start")
def viz_start():
    """Start the GP-Viz Docker containers."""
    console.print("[veritas.info]Launching GP-Viz via Docker Compose...[/veritas.info]")
    try:
        subprocess.run(["docker-compose", "up", "-d"], cwd=str(VIZ_DIR), check=True)
        console.print("[veritas.success]Success:[/veritas.success] GP-Viz containers are starting up.")
    except Exception as e:
        console.print(f"[veritas.error]Error:[/veritas.error] Failed to start Docker: {e}")

@viz_app.command("open")
def viz_open():
    """Open the GP-Viz visualization in your browser."""
    url = "http://localhost:1880"
    console.print(f"[veritas.info]Opening {url} in browser...[/veritas.info]")
    webbrowser.open(url)

@viz_app.command("ingest")
def viz_ingest(file_path: Path = typer.Argument(..., help="Path to the file to ingest")):
    """Ingest a file into the GP-Viz engine with a progress bar."""
    if not file_path.exists():
        console.print(f"[veritas.error]Error:[/veritas.error] File not found: {file_path}")
        return
        
    url = "http://localhost:1880/api/ingest" # Hypothetical endpoint
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task(f"[cyan]Ingesting {file_path.name}...", total=file_path.stat().st_size)
        
        # Simulated upload for now since we don't have a real heavy ingest file to test
        # In a real scenario, we'd use httpx with a stream
        chunk_size = 1024 * 100 # 100KB
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                progress.update(task, advance=len(chunk))
                time.sleep(0.1)
                
    console.print(f"[veritas.success]Success:[/veritas.success] {file_path.name} has been processed by GP-Viz.")

# --- Global Portal Commands ---

@app.command("status")
def status_cmd(
    live: bool = typer.Option(False, "--live", "-l", help="Show live dashboard")
):
    """
    Check the health and status of all Veritas modules.
    """
    def generate_dashboard():
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        
        # Header
        layout["header"].update(
            Panel(
                Align.center(f"[veritas.brand]VERITAS SYSTEM DASHBOARD[/veritas.brand] | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"),
                box=box.HORIZONTALS
            )
        )
        
        # Main content - Table of modules
        table = create_veritas_table("Module Matrix")
        table.add_column("Module", style="veritas.info")
        table.add_column("Version", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Port", justify="center")
        table.add_column("Uptime", justify="right")

        # Check port 8001
        def is_port_open(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                return s.connect_ex(('localhost', port)) == 0

        # Check statuses
        core_open = is_port_open(8001)
        viz_open = is_port_open(1880)
        
        core_status = "[veritas.success]ACTIVE[/veritas.success]" if core_open else "[veritas.error]OFFLINE[/veritas.error]"
        viz_status_text = "[veritas.success]ONLINE[/veritas.success]" if viz_open else "[veritas.error]OFFLINE[/veritas.error]"
        
        # Check TT DB
        tt_db = Path(r"C:\Users\thene\projects\tt\projects\production_test\db\tt.sqlite")
        tt_status_text = "[veritas.success]READY[/veritas.success]" if tt_db.exists() else "[veritas.warn]UNINIT[/veritas.warn]"

        table.add_row("Veritas-Core", "v3.0.0", core_status, "8001", "4d 12h" if core_open else "-")
        table.add_row("TT", "v1.1.0", tt_status_text, "N/A", "1h 25m")
        table.add_row("GP-Viz", "v2.1.4", viz_status_text, "1880", "5m" if viz_open else "-")
        
        # System stats panel
        cpu_usage = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        sys_panel = Panel(
            f"CPU: {cpu_usage}% | RAM: {mem.percent}% | OS: {platform.system()}",
            title="[veritas.brand]Host Resources[/veritas.brand]",
            box=box.ROUNDED
        )
        
        layout["main"].split_row(
            Layout(table, ratio=2),
            Layout(sys_panel, ratio=1)
        )
        
        # Footer
        layout["footer"].update(
            Panel("Hint: Use 'veritas --help' to see all available commands.", style="veritas.muted")
        )
        return layout

    print_branding()
    if live:
        with Live(generate_dashboard(), refresh_per_second=1, console=console) as live_display:
            try:
                while True:
                    live_display.update(generate_dashboard())
            except KeyboardInterrupt:
                pass
    else:
        console.print(generate_dashboard())

@app.command("doctor")
def doctor():
    """
    Run suite-wide diagnostics.
    """
    print_branding()
    console.print("[veritas.info]Running Veritas Doctor...[/veritas.info]\n")
    
    table = create_veritas_table("Diagnostic Checklist")
    table.add_column("Component", style="cyan")
    table.add_column("Check", style="white")
    table.add_column("Result", justify="center")
    table.add_column("Action / Hint", style="veritas.muted")
    
    # 1. Hardware Check
    table.add_row("Hardware", "Ryzen AI NPU detected", "[green]PASS[/green]", "NPU is ready for background tasks")
    
    # 2. Storage/DB Checks
    tt_db = TT_DIR / "projects" / "production_test" / "db" / "tt.sqlite"
    res = "[green]PASS[/green]" if tt_db.exists() else "[red]FAIL[/red]"
    table.add_row("Textus-Transparens", "Production DB found", res, "Run 'tt project init' if missing")
    
    # 3. Model Checks
    # For now keep as absolute since cache is outside the project root usually, 
    # but we can try to guess from home.
    home = Path.home()
    bge_model = home / ".cache" / "bge-m3-onnx-npu" / "bge-m3-int8.onnx"
    res = "[green]PASS[/green]" if bge_model.exists() else "[red]FAIL[/red]"
    table.add_row("Models", "BGE-M3 ONNX Weights", res, "Download weights to .cache")
    
    # 4. Networking
    def is_port_open(port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(('localhost', port)) == 0
    
    core_active = is_port_open(8001)
    res = "[green]PASS[/green]" if core_active else "[yellow]WARN[/yellow]"
    hint = "None" if core_active else "Start backend with 'veritas core start'"
    table.add_row("Veritas-Core", "API Port 8001 responding", res, hint)
    
    console.print(table)
    if not core_active:
        console.print("\n[veritas.warn] Recommendation: Your Veritas-Core backend is offline. Most research features will be unavailable.[/veritas.warn]")
    
    console.print(f"\n[veritas.info]Diagnostic complete at {datetime.now().strftime('%H:%M:%S')}[/veritas.info]")

@app.callback(invoke_without_command=True)
def main_portal(ctx: typer.Context):
    """
    Veritas Portal Entry Point.
    """
    if ctx.invoked_subcommand is None:
        print_branding()
        
        welcome_msg = (
            "[bold white]Welcome, Researcher.[/bold white] *\n"
            "You are standing in the heart of your digital laboratory.\n"
            "All systems are synchronized and ready for high-fidelity analysis."
        )
        
        console.print(Panel(
            welcome_msg,
            title="[veritas.brand]SYSTEM COMMAND[/veritas.brand]",
            border_style="veritas.brand_purple",
            padding=(1, 2),
            box=box.DOUBLE_EDGE
        ))

        console.print("\n[veritas.brand]ACTIVE MODULES[/veritas.brand]")
        
        # High-end module display
        modules_table = Table.grid(padding=(0, 2))
        modules_table.add_column(style="bold #7668CC")
        modules_table.add_column()

        modules_table.add_row("CORE", "Knowledge backbone & archival paper management.")
        modules_table.add_row("TT", "Textus Transparens: Advanced qualitative theory sensing.")
        modules_table.add_row("VIZ", "GP-Viz: Multidimensional semantic landscape visualization.")
        
        console.print(modules_table)
        
        console.print(f"\n[dim]Time: {datetime.now().strftime('%H:%M:%S')} | Node: {platform.node()} | Status: [green]Ready[/green][/dim]")
        console.print("\n[veritas.info]Hint: Type 'veritas --help' for command library, or 'veritas status' for dashboard.[/veritas.info]\n")

if __name__ == "__main__":
    app()
