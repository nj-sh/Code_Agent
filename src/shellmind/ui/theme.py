"""
Theme support for ShellMind's terminal UI.

Provides light and dark color schemes that can be toggled
at runtime. The default dark theme matches ShellMind's classic
green/black/orange look.
"""

from dataclasses import dataclass, field


@dataclass
class Theme:
    """A color theme with named roles mapped to ANSI codes."""

    name: str

    # Core ANSI codes
    reset: str = "\033[0m"
    bold: str = "\033[1m"
    dim: str = "\033[2m"
    italic: str = "\033[3m"

    # Role colors
    accent: str = "\033[38;5;214m"  # Orange (borders, headers, dirs)
    success: str = "\033[92m"       # Green (success messages)
    warning: str = "\033[93m"       # Yellow (warnings, tips)
    error: str = "\033[91m"         # Red (errors)
    muted: str = "\033[90m"         # Gray (secondary info)
    line: str = "\033[38;5;236m"    # Dark gray (borders)
    think: str = "\033[38;5;245m"   # Light gray (thinking text)
    token: str = "\033[38;5;214m"   # Orange (token count)

    cursor: str = ""
    background: str = ""
    foreground: str = ""

    @classmethod
    def dark(cls) -> "Theme":
        """Default dark theme — green/black/orange."""
        return cls(
            name="dark",
            accent="\033[38;5;214m",
            success="\033[92m",
            warning="\033[93m",
            error="\033[91m",
            muted="\033[90m",
            line="\033[38;5;236m",
            think="\033[38;5;245m",
            token="\033[38;5;214m",
        )

    @classmethod
    def light(cls) -> "Theme":
        """Light theme — dark text on light background."""
        return cls(
            name="light",
            accent="\033[34m",       # Blue
            success="\033[32m",      # Green
            warning="\033[33m",      # Yellow/amber
            error="\033[31m",        # Red
            muted="\033[90m",        # Gray
            line="\033[37m",         # Light gray
            think="\033[90m",        # Dark gray
            token="\033[34m",        # Blue
        )

    @classmethod
    def from_name(cls, name: str) -> "Theme":
        """Get a theme by name. Falls back to dark."""
        return {"dark": cls.dark(), "light": cls.light()}.get(name.lower(), cls.dark())


# Active theme singleton
_active_theme: Theme = Theme.dark()


def get_active() -> Theme:
    """Get the currently active theme."""
    return _active_theme


def set_active(theme: Theme | str) -> None:
    """Set the active theme by Theme object or name string."""
    global _active_theme  # noqa: PLW0603
    if isinstance(theme, str):
        theme = Theme.from_name(theme)
    _active_theme = theme


def available_themes() -> list[str]:
    """List available theme names."""
    return ["dark", "light"]
