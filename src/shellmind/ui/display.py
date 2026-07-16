"""
Terminal display helpers for ShellMind.

Provides formatted output for headers, thinking blocks, tool calls,
results, summaries, progress tracking, and status messages.
All methods use the active Theme for consistent coloring.

Supports verbosity levels: quiet (minimal), normal (default), verbose (detailed).
"""

import os
import sys
import textwrap

from shellmind.config import get_terminal_width
from shellmind.ui.theme import get_active, Theme


# Verbosity levels
VERBOSITY_QUIET = 0
VERBOSITY_NORMAL = 1
VERBOSITY_VERBOSE = 2
VERBOSITY_DEBUG = 3

_verbosity = VERBOSITY_NORMAL


def set_verbosity(level: int) -> None:
    """Set the global verbosity level."""
    global _verbosity  # noqa: PLW0603
    _verbosity = level


def get_verbosity() -> int:
    """Get the current verbosity level."""
    return _verbosity


class ProgressTracker:
    """Tracks and displays a todo-checklist during task execution."""

    def __init__(self):
        self._steps: list[dict] = []
        self._current_step = 0
        self._total_steps = 0

    def reset(self) -> None:
        self._steps = []
        self._current_step = 0
        self._total_steps = 0

    def set_plan(self, steps: list[str]) -> None:
        self.reset()
        for step in steps:
            self._steps.append({"label": step, "status": "todo"})
        self._total_steps = len(steps)

    def start_step(self, index: int = 0, label: str = "") -> None:
        if label and index < len(self._steps):
            self._steps[index]["label"] = label
        if index < len(self._steps):
            self._steps[index]["status"] = "doing"
            self._current_step = index

    def complete_step(self, index: int, success: bool = True) -> None:
        if index < len(self._steps):
            self._steps[index]["status"] = "done" if success else "failed"

    @property
    def is_active(self) -> bool:
        return self._total_steps > 0

    def render(self, display: "Display") -> None:
        if not self._steps or get_verbosity() < VERBOSITY_NORMAL:
            return

        theme = get_active()
        w = display._wrap()
        from shellmind.ui.theme import is_plain
        plain = is_plain()
        h_bar = "-" if plain else "─"
        v_bar = "|" if plain else "│"
        corner_tl = "+" if plain else "├"
        corner_tr = "+" if plain else "┤"
        check = "[v]" if plain else "[✓]"
        cross = "[x]" if plain else "[✗]"
        doing_char = ">" if plain else "[~]"
        todo_char = "." if plain else "[ ]"

        print()
        header = f" Progress [{self._current_step + 1}/{self._total_steps}] " if self._total_steps > 0 else " Progress "
        line_width = min(w - 4, 50)
        print(f"{theme.accent}{corner_tl}{h_bar * line_width}{corner_tr}{theme.reset}")
        print(f"{theme.accent}{v_bar}{theme.reset} {theme.bold}{header:<{line_width - 2}}{theme.reset} {theme.accent}{v_bar}{theme.reset}")

        for i, step in enumerate(self._steps):
            label = step["label"]
            status = step["status"]
            if status == "done":
                icon = f"{theme.success}{check}{theme.reset}"
                label_text = f"{theme.dim}{label}{theme.reset}"
            elif status == "doing":
                icon = f"{theme.warning}{doing_char}{theme.reset}"
                label_text = f"{theme.bold}{theme.accent}{label}{theme.reset}"
            elif status == "failed":
                icon = f"{theme.error}{cross}{theme.reset}"
                label_text = f"{theme.error}{label}{theme.reset}"
            else:
                icon = f"{theme.muted}{todo_char}{theme.reset}"
                label_text = f"{theme.muted}{label}{theme.reset}"

            print(f"  {icon} {label_text}")

        print(f"{theme.accent}{corner_tl}{h_bar * line_width}{corner_tr}{theme.reset}")


class Display:
    """Collection of terminal display utilities using the active theme."""

    def __init__(self):
        self.width = get_terminal_width()
        self.tracker = ProgressTracker()

    def refresh_width(self) -> None:
        self.width = get_terminal_width()

    def _wrap(self, width: int | None = None) -> int:
        w = width or self.width
        return min(w, 72)

    def reset_progress(self) -> None:
        self.tracker.reset()

    def set_plan(self, steps: list[str]) -> None:
        self.tracker.set_plan(steps)

    def show_progress(self) -> None:
        if self.tracker.is_active:
            self.tracker.render(self)

    def step_start(self, index: int, label: str = "") -> None:
        self.tracker.start_step(index, label)
        self.show_progress()

    def step_done(self, index: int, success: bool = True) -> None:
        self.tracker.complete_step(index, success)
        self.show_progress()

    # ─── Header / Banner ──────────────────────────────────────────────

    def header(self, model: str, cwd: str, memory_name: str,
               last_summary: str = "") -> None:
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
        verbosity_names = {0: "quiet", 1: "normal", 2: "verbose", 3: "debug"}
        print(f"  {theme.warning}[i]{theme.reset} {theme.dim}Theme: {theme_t} | :help for commands{theme.reset}")
        print(f"  {theme.line}{'-' * w}{theme.reset}")

    # ─── Thinking Block ───────────────────────────────────────────────

    def thinking(self, thought: str) -> None:
        if get_verbosity() < VERBOSITY_NORMAL:
            return  # Skip thinking blocks in quiet mode
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
        if get_verbosity() < VERBOSITY_NORMAL:
            return  # Skip tool call display in quiet mode
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
        theme = get_active()
        if cancelled:
            tag = f"{theme.warning}!! Cancelled{theme.reset}"
        elif success:
            tag = f"{theme.success}>> Success{theme.reset}"
        else:
            tag = f"{theme.error}>> Failed{theme.reset}"
        print(f"  {tag} {theme.muted}({duration:.2f}s){theme.reset}")

        if get_verbosity() < VERBOSITY_NORMAL:
            return  # Skip output in quiet mode

        output = output.strip()
        if not output:
            if not success and not cancelled:
                print(f"    {theme.dim}(empty){theme.reset}")
            return

        w = self._wrap() - 4
        max_lines = 30 if get_verbosity() >= VERBOSITY_VERBOSE else 15
        lines = output.split("\n")
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
        if get_verbosity() < VERBOSITY_NORMAL:
            # Quiet mode: just print the first line
            first = text.strip().split("\n")[0][:80]
            print(f"  {get_active().success}✓ {first}{get_active().reset}")
            return
        theme = get_active()
        w = self._wrap()
        print(f"\n{theme.success}+{'-' * (w - 2)}+{theme.reset}")
        for line in text.strip().split("\n"):
            for wl in textwrap.wrap(line, width=w - 4):
                print(f"{theme.success}| {wl:<{w - 4}} |{theme.reset}")
        print(f"{theme.success}+{'-' * (w - 2)}+{theme.reset}")

    # ─── Req_Success Summary ───────────────────────────────────────────

    def req_success_summary(
        self,
        commands: list[str],
        tokens_in: int = 0,
        tokens_out: int = 0,
        duration: float = 0.0,
        changes: list[str] | None = None,
    ) -> None:
        """Display filtered summary when ShellMind Req_Success is detected.

        Shows: commands executed, tokens used, time taken, changes made.
        Uses a clean, minimal format optimized for small models.
        """
        theme = get_active()
        from shellmind.ui.theme import is_plain
        plain = is_plain()
        h_bar = "-" if plain else "─"
        v_bar = "|" if plain else "│"
        corner_tl = "+" if plain else "├"
        corner_bl = "+" if plain else "└"
        tick = "[v]" if plain else "✓"

        w = self._wrap()
        line_w = min(w - 4, 48)

        print(f"\n{theme.success}{corner_tl}{h_bar * line_w}{'┤' if not plain else '+'}{theme.reset}")
        print(f"{theme.success}{v_bar}{theme.reset} {theme.bold}{tick} Task Complete{theme.reset}")

        if changes:
            print(f"{theme.success}{v_bar}{theme.reset} {theme.muted}Changes:{theme.reset}")
            for c in changes:
                if len(c) > line_w - 6:
                    c = c[:line_w - 9] + "..."
                print(f"{theme.success}{v_bar}{theme.reset}   {theme.dim}{c}{theme.reset}")

        if commands:
            print(f"{theme.success}{v_bar}{theme.reset} {theme.muted}Commands:{theme.reset}")
            for cmd in commands[:3]:  # Show top 3 commands
                if len(cmd) > line_w - 6:
                    cmd = cmd[:line_w - 9] + "..."
                print(f"{theme.success}{v_bar}{theme.reset}   {theme.dim}$ {cmd}{theme.reset}")
            if len(commands) > 3:
                print(f"{theme.success}{v_bar}{theme.reset}   {theme.muted}... and {len(commands) - 3} more{theme.reset}")

        # Summary line
        summary_parts = []
        if tokens_in or tokens_out:
            summary_parts.append(f"{tokens_in}+{tokens_out} tokens")
        if duration:
            summary_parts.append(f"{duration:.1f}s")
        if summary_parts:
            print(f"{theme.success}{v_bar}{theme.reset} {theme.muted}{' | '.join(summary_parts)}{theme.reset}")

        print(f"{theme.success}{corner_bl}{h_bar * line_w}{'┘' if not plain else '+'}{theme.reset}")

    # ─── Streaming Output ─────────────────────────────────────────────

    def stream_line(self, line: str) -> None:
        """Display a line of streaming command output."""
        if get_verbosity() >= VERBOSITY_VERBOSE:
            theme = get_active()
            print(f"  {theme.muted}|{theme.reset} {line}")

    # ─── Status / Info / Error ────────────────────────────────────────

    @staticmethod
    def error(msg: str) -> None:
        theme = get_active()
        print(f"  {theme.error}x {msg}{theme.reset}")

    @staticmethod
    def info(msg: str) -> None:
        if get_verbosity() < VERBOSITY_NORMAL:
            return  # Skip info in quiet mode
        theme = get_active()
        print(f"  {theme.muted}{msg}{theme.reset}")

    @staticmethod
    def warning(msg: str) -> None:
        theme = get_active()
        print(f"  {theme.warning}! {msg}{theme.reset}")

    @staticmethod
    def success(msg: str) -> None:
        theme = get_active()
        print(f"  {theme.success}+ {msg}{theme.reset}")

    @staticmethod
    def raw(text: str) -> None:
        print(text)
