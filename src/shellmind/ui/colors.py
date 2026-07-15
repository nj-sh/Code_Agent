"""
ANSI color codes for ShellMind's terminal UI.

Theme: Green/Black/Orange (inspired by classic terminals).
"""


class Color:
    """ANSI color codes for the green/black/orange terminal theme."""

    ORANGE = "\033[38;5;214m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    BLUE = "\033[38;5;214m"  # Same orange for tool calls
    MAGENTA = "\033[38;5;205m"
    THINK = "\033[38;5;245m"
    TOKEN = "\033[38;5;214m"  # Orange for token count
    LINE = "\033[38;5;236m"

    # Aliases for theme clarity
    CYAN = ORANGE
    ACCENT = ORANGE
    SUCCESS = GREEN
    WARNING = YELLOW
    ERROR = RED
    MUTED = GRAY


# Shorthand
C = Color
