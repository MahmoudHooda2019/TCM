from colorama import Fore, Style, init
init(autoreset=True)


def print_banner():
    art = r"""
  _______    _____   __  __ 
 |__   __|  / ____| |  \/  |
    | |    | |      | \  / |
    | |    | |      | |\/| |
    | |    | |____  | |  | |
    |_|     \_____| |_|  |_|
                                                          
"""
    subtitle  = "  Telegram  Channel  Migrator"
    separator = "  ─" + "─" * len(subtitle)

    print()
    print(Fore.CYAN + separator)
    print(Fore.CYAN + art, end="")
    print(Fore.CYAN + subtitle)
    print(Fore.CYAN + art, end="")
    print(Fore.CYAN + separator)
    print(Style.RESET_ALL)


def print_message(msg, color="green"):
    colors = {
        "green":  Fore.GREEN,
        "red":    Fore.RED,
        "yellow": Fore.YELLOW,
        "cyan":   Fore.CYAN,
    }
    c = colors.get(color, Fore.GREEN)
    print(c + msg + Style.RESET_ALL)


def print_section(title):
    """Thin visual separator before each input group."""
    print(Fore.CYAN + f"\n  ── {title} ──" + Style.RESET_ALL)
