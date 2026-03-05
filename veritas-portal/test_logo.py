from rich.console import Console
from rich.theme import Theme

VERITAS_THEME = Theme({
    "veritas.brand": "bold deep_sky_blue1",
})
console = Console(theme=VERITAS_THEME)

LOGO = r"""[veritas.brand]
 __      __ ______ _____  _____ _______        _____ 
 \ \    / /|  ____|  __ \|_   _|__   __|      / ____|
  \ \  / / | |__  | |__) | | |    | |  /\    | (___  
   \ \/ /  |  __| |  _  /  | |    | | /  \    \___ \ 
    \  /   | |____| | \ \ _| |_   | |/ ____ \ ____) |
     \/    |______|_|  \_\_____|  |_/_/    \_\_____/
[/veritas.brand]"""

console.print(LOGO)
