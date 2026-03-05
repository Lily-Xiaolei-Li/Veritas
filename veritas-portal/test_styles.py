from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.columns import Columns

console = Console()

# Gemini-like colors: Blue -> Purple -> Pink
# deep_sky_blue1, medium_purple1, hot_pink

def print_grand_logo():
    logo = [
        r"  __      ________ _____  _____ _______       _____ ",
        r"  \ \    / /  ____|  __ \|_   _|__   __|     / ____|",
        r"   \ \  / /| |__  | |__) | | |    | |  /\   | (___  ",
        r"    \ \/ / |  __| |  _  /  | |    | | /  \   \___ \ ",
        r"     \  /  | |____| | \ \ _| |_   | |/ ____ \ ____) |",
        r"      \/   |______|_|  \_\_____|  |_/_/    \_\_____/"
    ]
    
    colors = ["#4285F4", "#5C76E0", "#7668CC", "#9159B8", "#AB4AA4", "#C53B90"]
    
    console.print()
    for i, line in enumerate(logo):
        console.print(Text(line, style=colors[i]))
    console.print(Text("             A C A D E M I C   R E S E A R C H   S U I T E", style="dim italic"))
    console.print()

print_grand_logo()

# Let's try another one, more blocky like the image
def print_block_logo():
    # Font: ANSI Shadow or similar style manually
    logo = [
        "██╗   ██╗███████╗██████╗ ██╗████████╗ █████╗ ███████╗",
        "██║   ██║██╔════╝██╔══██╗██║╚══██╔══╝██╔══██╗██╔════╝",
        "██║   ██║█████╗  ██████╔╝██║   ██║   ███████║███████╗",
        "╚██╗ ██╔╝██╔══╝  ██╔══██╗██║   ██║   ██╔══██║╚════██║",
        " ╚████╔╝ ███████╗██║  ██║██║   ██║   ██║  ██║███████║",
        "  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝"
    ]
    
    # Horizontal gradient
    colors = ["#4facfe", "#48c6ef", "#00f2fe", "#4facfe", "#8093f1", "#7028e4", "#b122e5"]
    
    console.print("--- BLOCK LOGO (HORIZONTAL GRADIENT) ---")
    for line in logo:
        # We can't easily do character-by-character gradient in one print without complex logic
        # but we can do a nice blue/purple theme
        console.print(Text(line, style="bold #4facfe"))

print_block_logo()
