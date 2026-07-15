"""
Terminal display helpers for ShellMind.

Provides formatted output for headers, thinking blocks, tool calls,
results, summaries, progress tracking, and status messages.
All methods use the active Theme for consistent coloring.
"""

import os
import sys
import textwrap

from shellmind.config import get_terminal_width
from shellmind.ui.theme import get_active, Theme


class ProgressTracker:
    """Tracks and displays a todo-checklist during task execution."""

    def __init__(self):
        self._steps: list[dict] = []  # {label, status}
        self._current_step = 0
        self._total_steps = 0

    def reset(self) -> None:
        """Clear all tracked steps."""
        self._steps = []
        self._current_step = 0
        self._total_steps = 0

    def set_plan(self, steps: list[str]) -> None:
        """Set the plan from a list of step descriptions."""
        self.reset()
        for step in steps:
            self._steps.append({"label": step, "status": "todo"})
        self._total_steps = len(steps)

    def start_step(self, index: int = 0, label: str = "") -> None:
        """Mark a step as in-progress."""
        if label and index < len(self._steps):
            self._steps[index]["label"] = label
        if index < len(self._steps):
            self._steps[index]["status"] = "doing"
            self._current_step = index

    def complete_step(self, index: int, success: bool = True) -> None:
        """Mark a step as done or failed."""
        if index < len(self._steps):
            self._steps[index]["status"] = "done" if success else "failed"

    @property
    def is_active(self) -> bool:
        return self._total_steps > 0

    def render(self, display: "Display") -> None:
        """Render the current progress to the terminal."""
        if not self._steps:
            return

        theme = get_active()
        w = display._wrap()
        print()

        # Header with step counter
        header = f" Progress [{self._current_step + 1}/{self._total_steps}] " if self._total_steps > 0 else " Progress "
        print(f"{theme.accent}├{'─' * (w - 4)}┤{theme.reset}")
        print(f"{theme.accent}│{theme.reset}{theme.bold}{header:<{w - 4}}{theme.reset}{theme.accent}│{theme.reset}")

        # Each step
        for i, step in enumerate(self._steps):
            label = step["label"]
            status = step["status"]
            if status == "done":
                icon = f"{theme.success}[✓]{theme.reset}"
                label_text = f"{theme.dim}{label}{theme.reset}"
            elif status == "doing":
                icon = f"{theme.warning}[~]{theme.reset}"
                label_text = f"{theme.bold}{theme.accent}{label}{theme.reset}"
            elif status == "failed":
                icon = f"{theme.error}[✗]{theme.reset}"
                label_text = f"{theme.error}{label}{theme.reset}"
            else:  # todo
                icon = f"{theme.muted}[ ]{theme.reset}"
                label_text = f"{theme.muted}{label}{theme.reset}"

            line = f"  {icon} {label_text}"
            if len(line) > w - 2:
                line = line[:w - 5] + "..."
            print(line)

        print(f"{theme.accent}├{'─' * (w - 4)}┤{theme.reset}")


class Display:
    """Collection of terminal display utilities using the active theme."""

    def __init__(self):
        self.width = get_terminal_width()
        self.tracker = ProgressTracker()

    def refresh_width(self) -> None:
        """Re-detect terminal width."""
        self.width = get_terminal_width()

    def _wrap(self, width: int | None = None) -> int:
        """Get effective wrap width."""
        w = width or self.width
        return min(w, 72)

    def reset_progress(self) -> None:
        """Reset the progress tracker before a new task."""
        self.tracker.reset()

    def set_plan(self, steps: list[str]) -> None:
        """Set the execution plan for the current task."""
        self.tracker.set_plan(steps)

    def show_progress(self) -> None:
        """Render the current progress checklist."""
        if self.tracker.is_active:
            self.tracker.render(self)

    def step_start(self, index: int, label: str = "") -> None:
        """Mark a step as in-progress and render."""
        self.tracker.start_step(index, label)
        self.show_progress()

    def step_done(self, index: int, success: bool = True) -> None:
        """Mark a step as complete and render."""
        self.tracker.complete_step(index, success)
        self.show_progress()

    # ─── Header / Banner ──────────────────────────────────────────────

    def header(self, model: str, cwd: str, memory_name: str,
               last_summary: str = "") -> None:
        """Render the startup banner."""
        theme = get_active()
        w = self._wrap()
        print(f"\n{theme.bold}{theme.accent}+{'=' * (w - 2)}+{theme.reset}")
        title = "* ShellMind v5"
        pad_left = (w - 2 - len(title)) // 2
        pad_right = w - 2 - len(title) - pad_left
        print(f"{theme.bold}{theme.accent}|{' ' * pad_left}{title}{' ' * pad_right}|{theme.reset}")
        print(f"{theme.bold}{theme.accent}+{'=' * (w - 2)}+{theme.reset}")
        print(f"  {theme.muted}Model:  {theme.warning}{model}{theme.reset}")
        home = os.path.expanduser("~")
        print(f"  {theme.muted}CWD:    {theme.accent}{cwd.replace(home, '~')}{theme.reset}")
        print(f"  {theme.muted}Memory: {theme.dim}{memory_name}{theme.reset}")
        if last_summary:
            last = last_summary.split("\n")[0][:60]
            print(f"  {theme.muted}Last:   {theme.dim}{last}{theme.reset}")
        theme_t = get_active().name
        print(f"  {theme.warning}[i]{theme.reset} {theme.dim}Theme: {theme_t} | :help for commands{theme.reset}")
        print(f"  {theme.line}{'-' * w}{theme.reset}")

    # ─── Thinking Block ───────────────────────────────────────────────

    def thinking(self, thought: str) -> None:
        """Display a thinking block in a distinctive box."""
        theme = get_active()
        w = self._wrap()
        print(f"\n{theme.accent}+{'~' * (w - 2)}+{theme.reset}")
        label = "~ Thinking ~"
        print(f"{theme.accent}|{theme.reset} {theme.bold}{theme.accent}{label}{theme.reset}"
              f"{' ' * (w - 4 - len(label))}{theme.accent}|{theme.reset}")
        print(f"{theme.accent}+{'-' * (w - 2)}+{theme.reset}")
        for line in thought.strip().split("\n"):
            for wl in textwrap.wrap(line, width=w - 6):
                print(f"{theme.accent}|{theme.reset} {theme.dim}{wl:<{w - 4}}{theme.reset} {theme.accent}|{theme.reset}")
        print(f"{theme.accent}+{'~' * (w - 2)}+{theme.reset}")

    # ─── Tool Call ────────────────────────────────────────────────────

    def tool_call(self, name: str, args: dict) -> None:
        """Display a tool invocation."""
        theme = get_active()
        parts = []
        for k, v in args.items():
            if isinstance(v, str) and len(v) > 60:
                parts.append(f"{k}={v[:57]}...")
            else:
                parts.append(f"{k}={v}")
        desc = ", ".join(parts[:2])
        if len(parts) > 2:
            desc += " ..."

        print(f"\n{theme.accent}>>{theme.reset} {theme.bold}{name}{theme.reset} {theme.muted}({desc}){theme.reset}")

    # ─── Tool Result ──────────────────────────────────────────────────

    def tool_result(self, success: bool, output: str, duration: float,
                    cancelled: bool = False) -> None:
        """Display a tool execution result."""
        theme = get_active()
        if cancelled:
            tag = f"{theme.warning}!! Cancelled{theme.reset}"
        elif success:
            tag = f"{theme.success}>> Success{theme.reset}"
        else:
            tag = f"{theme.error}>> Failed{theme.reset}"
        print(f"  {tag} {theme.muted}({duration:.2f}s){theme.reset}")

        output = output.strip()
        if not output:
            if not success and not cancelled:
                print(f"    {theme.dim}(empty){theme.reset}")
            return

        w = self._wrap() - 4
        lines = output.split("\n")
        max_lines = 15
        display_lines = lines[:max_lines]
        print(f"  {theme.line}+{'.' * (w - 2)}+{theme.reset}")
        for line in display_lines:
            if len(line) > w - 4:
                line = line[:w - 7] + "..."
            print(f"  {theme.line}|{theme.reset} {line:<{w - 4}} {theme.line}|{theme.reset}")
        if len(lines) > max_lines:
            print(f"  {theme.line}|{theme.reset} {theme.muted}... and {len(lines) - max_lines} more{theme.reset}"
                  f"  {theme.line}|{theme.reset}")
        print(f"  {theme.line}+{'.' * (w - 2)}+{theme.reset}")

    # ─── Summary ──────────────────────────────────────────────────────

    def summary(self, text: str) -> None:
        """Display the final task summary in a bordered box."""
        theme = get_active()
        w = self._wrap()
        print(f"\n{theme.success}+{'-' * (w - 2)}+{theme.reset}")
        for line in text.strip().split("\n"):
            for wl in textwrap.wrap(line, width=w - 4):
                print(f"{theme.success}| {wl:<{w - 4}} |{theme.reset}")
        print(f"{theme.success}+{'-' * (w - 2)}+{theme.reset}")

    # ─── Status / Info / Error ────────────────────────────────────────

    @staticmethod
    def error(msg: str) -> None:
        """Display an error message."""
        theme = get_active()
        print(f"  {theme.error}x {msg}{theme.reset}")

    @staticmethod
    def info(msg: str) -> None:
        """Display an info message."""
        theme = get_active()
        print(f"  {theme.muted}{msg}{theme.reset}")

    @staticmethod
    def warning(msg: str) -> None:
        """Display a warning message."""
        theme = get_active()
        print(f"  {theme.warning}! {msg}{theme.reset}")

    @staticmethod
    def success(msg: str) -> None:
        """Display a success message."""
        theme = get_active()
        print(f"  {theme.success}+ {msg}{theme.reset}")

    @staticmethod
    def raw(text: str) -> None:
        """Print raw text (no theme colors)."""
        print(text)
