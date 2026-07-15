"""
CLI input prompt builder for ShellMind.
Uses the active theme for consistent coloring.
"""

import os

from shellmind.ui.theme import get_active
from shellmind.config import get_terminal_width


class Prompt:
    """Builds the input prompt string with directory, mode, and token info."""

    @staticmethod
    def build(cwd: str, mode: str, tokens: int) -> str:
        """Build the input prompt string."""
        theme = get_active()
        home = os.path.expanduser("~")
        p = cwd.replace(home, "~")
        mode_tag = f"{theme.success}A{theme.reset}" if mode == "auto" else f"{theme.warning}M{theme.reset}"
        token_tag = f"{theme.token}[{tokens}t]{theme.reset}"
        return f"{theme.accent}{p}{theme.reset} {mode_tag} {token_tag} {theme.success}>{theme.reset} "
