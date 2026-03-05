from rich.theme import Theme
from rich.console import Console
from rich.table import Table
from rich.text import Text
from rich import box

# Veritas High-End Theme
VERITAS_THEME = Theme({
    "veritas.brand": "bold #4285F4",    # Google Blue
    "veritas.brand_light": "#5C76E0",
    "veritas.brand_purple": "#9159B8",
    "veritas.brand_pink": "#C53B90",
    "veritas.success": "bold #34A853", # Google Green
    "veritas.warn": "bold #FBBC05",    # Google Yellow
    "veritas.error": "bold #EA4335",   # Google Red
    "veritas.info": "italic cyan",
    "veritas.muted": "dim white",
    "veritas.id": "bold #7668CC",
})

console = Console(theme=VERITAS_THEME)

def create_veritas_table(title: str) -> Table:
    return Table(
        title=title,
        box=box.SIMPLE_HEAVY,
        header_style="bold #4285F4",
        row_styles=["none", "dim"],
        title_style="bold #4285F4"
    )

def print_branding(quiet: bool = False):
    if quiet:
        return
        
    logo = [
        r"  __      ________ _____  _____ _______       _____ ",
        r"  \ \    / /  ____|  __ \|_   _|__   __|     / ____|",
        r"   \ \  / /| |__  | |__) | | |    | |  /\   | (___  ",
        r"    \ \/ / |  __| |  _  /  | |    | | /  \   \___ \ ",
        r"     \  /  | |____| | \ \ _| |_   | |/ ____ \ ____) |",
        r"      \/   |______|_|  \_\_____|  |_/_/    \_\_____/"
    ]
    
    # Vertical gradient colors (Blue -> Purple -> Pink)
    colors = ["#4285F4", "#5C76E0", "#7668CC", "#9159B8", "#AB4AA4", "#C53B90"]
    
    console.print()
    for i, line in enumerate(logo):
        console.print(Text(line, style=colors[i]))
    
    subtitle = Text("             A C A D E M I C   R E S E A R C H   S U I T E", style="dim italic")
    console.print(subtitle)
    console.print()
