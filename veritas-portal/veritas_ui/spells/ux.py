from rich.panel import Panel
from rich.text import Text
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TimeRemainingColumn
from rich.table import Table
from rich import box
import time

# Magical Colors
PURPLE = "#B57EDC"
GOLD = "#FFD700"
CYAN = "#00FFFF"
MAGENTA = "#FF00FF"

class SpellUX:
    @staticmethod
    def print_spell_header(title: str, subtitle: str):
        header = Text()
        header.append(f"✨ {title.upper()} ✨", style=f"bold {GOLD}")
        
        panel = Panel(
            Align.center(header),
            subtitle=Text(subtitle, style=f"italic {PURPLE}"),
            border_style=MAGENTA,
            box=box.DOUBLE_EDGE,
            padding=(1, 2)
        )
        console.print(panel)

    @staticmethod
    def get_magical_spinner(text: str):
        return console.status(f"[{GOLD}]{text}[/{GOLD}]", spinner="arc")

    @staticmethod
    def print_fizzle(error_msg: str):
        content = Text()
        content.append("🔮 MAGIC FIZZLE 🔮\n\n", style="bold red")
        content.append(error_msg, style=PURPLE)
        
        panel = Panel(
            content,
            title="[bold red]Interrupt[/bold red]",
            border_style="red",
            padding=(1, 2)
        )
        console.print(panel)

    @staticmethod
    def create_verification_table(title: str) -> Table:
        table = Table(
            title=Text(f"📜 {title}", style=GOLD),
            box=box.HORIZONTALS,
            header_style=f"bold {CYAN}",
            border_style=PURPLE,
            row_styles=["none", "dim"]
        )
        return table

# To be used in main portal for consistency
from rich.align import Align
from veritas_ui.common import console
