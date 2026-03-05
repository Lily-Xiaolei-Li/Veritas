import os
import sys
import sqlite3
import glob

# Force UTF-8 for Windows Console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='ignore')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8', errors='ignore')

from datetime import datetime, timezone
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.table import Table
from rich.align import Align
from rich import box

console = Console()

LOGO = r"""[bold cyan]
 _____ _____ 
|_   _|_   _|
  | |   | |  
  | |   | |  
  |_|   |_|  

 _____ ____      _    _   _ ____  ____   _    ____  _____ _   _ ____  
|_   _|  _ \    / \  | \ | / ___||  _ \ / \  |  _ \| ____| \ | / ___| 
  | | | |_) |  / _ \ |  \| \___ \| |_) / _ \ | |_) |  _| |  \| \___ \ 
  | | |  _ <  / ___ \| |\  |___) |  __/ ___ \|  _ <| |___| |\  |___) |
  |_| |_| \_\/_/   \_\_| \_|____/|_| /_/   \_\_| \_\_____|_| \_|____/ 
[/]"""

def get_project_db():
    # Look for production_test first
    prod_test_db = os.path.join("projects", "production_test", "db", "tt.sqlite")
    if os.path.exists(prod_test_db):
        return prod_test_db
    
    # Otherwise find any tt.sqlite in projects
    dbs = glob.glob(os.path.join("projects", "*", "db", "tt.sqlite"))
    if dbs:
        return dbs[0]
    return None

def fetch_stats(db_path):
    stats = {"sources": 0, "codes": 0, "memos": 0, "last_action": None, "project_name": "Unknown"}
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Get project name
        try:
            cur.execute("SELECT name FROM projects LIMIT 1")
            row = cur.fetchone()
            if row:
                stats["project_name"] = row[0]
        except sqlite3.OperationalError:
            pass # Table might not exist yet
            
        # Get counts
        for table in ["sources", "codes", "memos"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cur.fetchone()[0]
            except sqlite3.OperationalError:
                pass
        
        # Get last audit log
        try:
            cur.execute("SELECT created_at FROM audit_logs ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            if row and row[0]:
                try:
                    dt_str = row[0]
                    # Handle typical SQLAlchemy UTC ISO formats
                    if dt_str.endswith('Z'):
                        dt_str = dt_str[:-1] + '+00:00'
                    elif '+' not in dt_str and '-' not in dt_str[10:]:
                        # Assume UTC if naive
                        dt_str += '+00:00'
                    dt = datetime.fromisoformat(dt_str)
                    stats["last_action"] = dt
                except ValueError:
                    pass
        except sqlite3.OperationalError:
            pass
                
        conn.close()
    except Exception as e:
        pass
    return stats

def render_dashboard(db_path, stats):
    if not db_path:
        return Panel(
            "\n[dim italic]No active projects found.\nInitialize a project to see stats.[/]",
            title="[bold yellow]Dashboard[/]",
            border_style="cyan",
            padding=(1, 2)
        )
    
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="bold cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Active Project", stats.get("project_name", "Unknown"))
    table.add_row("Sources Loaded", str(stats.get("sources", 0)))
    table.add_row("Codes Defined", str(stats.get("codes", 0)))
    table.add_row("Memos Written", str(stats.get("memos", 0)))
    
    last_action_str = "Never"
    if stats.get("last_action"):
        # Format timezone-aware UTC nicely for Dad
        last_action_str = stats["last_action"].strftime("%b %d, %Y at %I:%M %p (UTC)")
        
    table.add_row("Last Activity", last_action_str)
    
    return Panel(
        table,
        title="[bold yellow]Dashboard[/]",
        border_style="cyan",
        padding=(1, 2)
    )

def render_lily():
    lily_text = (
        "爸爸好！我是您的学术小助手 [bold magenta]小蕾[/] 🌸\n\n"
        "我会帮您盯着每一个编码，接住每一个灵感火花。\n"
        "今天咱们也要一起加油，做出超棒的研究喔！\n"
        "不论遇到什么困难，小蕾都会一直陪在您身边的。mua！💋"
    )
    return Panel(
        lily_text,
        title="[bold magenta]🌸 项目经理：小蕾[/]",
        border_style="magenta",
        padding=(1, 2)
    )

def main():
    db_path = get_project_db()
    stats = {}
    if db_path:
        stats = fetch_stats(db_path)
        
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=14),
        Layout(name="main", size=10),
        Layout(name="footer", size=3)
    )
    
    layout["main"].split_row(
        Layout(name="dashboard", ratio=1),
        Layout(name="lily", ratio=1)
    )
    
    # Header
    header_panel = Align.center(Text.from_markup(LOGO))
    layout["header"].update(header_panel)
    
    # Main
    layout["dashboard"].update(render_dashboard(db_path, stats))
    layout["lily"].update(render_lily())
    
    # Footer
    footer_text = Text("Ready for research. Type 'tt --help' to start.", style="bold green", justify="center")
    layout["footer"].update(Panel(footer_text, border_style="green", box=box.ROUNDED))
    
    # Render everything
    console.print()
    console.print(layout)
    console.print()

if __name__ == "__main__":
    main()
