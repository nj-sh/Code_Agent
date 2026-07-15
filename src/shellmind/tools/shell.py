"""
Shell command execution tools for ShellMind.

Provides execute_command and execute_file with full cross-platform support,
process management, and timeout handling.
"""

import os
import re
import time
from typing import Any

from shellmind.tools.base import BaseTool, ToolResult
from shellmind.platform import run_command, is_windows


class CdTool(BaseTool):
    """Change the current working directory with fuzzy matching."""

    @property
    def name(self) -> str:
        return "cd"

    @property
    def description(self) -> str:
        return "Change directory with fuzzy matching. Args: `path`"

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        if not path:
            return ToolResult(False, "No path provided", 0, self.name, kwargs)
        return self._change_dir(path)

    def _change_dir(self, path: str) -> ToolResult:
        """Change directory. Returns ToolResult with new path information."""
        t0 = time.time()
        expanded = os.path.expanduser(path)
        test = expanded if os.path.isabs(expanded) else os.path.join(os.getcwd(), expanded)
        test = os.path.normpath(test)

        # Exact match
        if os.path.isdir(test):
            os.chdir(test)
            new_cwd = os.getcwd()
            home = os.path.expanduser("~")
            return ToolResult(
                True,
                f"-> {new_cwd.replace(home, '~')}",
                time.time() - t0,
                self.name,
                {"command": f"cd {path}"},
            )

        # Fuzzy match
        parent = os.path.dirname(test) or "."
        target = os.path.basename(test)
        try:
            for entry in os.listdir(parent):
                fp = os.path.join(parent, entry)
                if os.path.isdir(fp) and (
                    entry == target or target.lower() in entry.lower()
                ):
                    os.chdir(fp)
                    new_cwd = os.getcwd()
                    home = os.path.expanduser("~")
                    return ToolResult(
                        True,
                        f"-> '{entry}'\n> {new_cwd.replace(home, '~')}",
                        time.time() - t0,
                        self.name,
                        {"command": f"cd {path}"},
                    )
        except (PermissionError, FileNotFoundError):
            pass

        # Show available dirs
        try:
            dirs = [d for d in os.listdir(os.getcwd()) if os.path.isdir(os.path.join(os.getcwd(), d))]
            hint = f"\nAvailable: {', '.join(dirs[:10])}" if dirs else ""
        except PermissionError:
            hint = ""

        return ToolResult(
            False,
            f"Directory not found: {path}{hint}",
            time.time() - t0,
            self.name,
            {"command": f"cd {path}"},
        )


class ExecuteCommandTool(BaseTool):
    """Run a bash/shell command and capture output."""

    @property
    def name(self) -> str:
        return "execute_command"

    @property
    def description(self) -> str:
        return "Run any shell command. Returns stdout/stderr + exit code."

    def execute(self, **kwargs: Any) -> ToolResult:
        command = kwargs.get("command", "")
        if not command:
            return ToolResult(False, "No command provided", 0, self.name, kwargs)

        t0 = time.time()
        cwd = kwargs.get("cwd")
        timeout = kwargs.get("timeout", 120)

        ec, output, timed_out = run_command(
            command=command,
            cwd=cwd,
            timeout=timeout,
        )

        return ToolResult(
            success=(ec == 0 and not timed_out),
            output=output,
            duration=time.time() - t0,
            tool=self.name,
            args=kwargs,
            cancelled=timed_out,
        )


class ExecuteFileTool(BaseTool):
    """Execute a script file as a shell command."""

    @property
    def name(self) -> str:
        return "execute_file"

    @property
    def description(self) -> str:
        return "Execute a script file as a shell command."

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        if not path:
            return ToolResult(False, "No path provided", 0, self.name, kwargs)

        t0 = time.time()
        full = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)

        if not os.path.isfile(full):
            return ToolResult(
                False, f"File not found: {path}",
                time.time() - t0, self.name, kwargs,
            )

        ec, output, timed_out = run_command(
            command=f'bash "{full}"' if not is_windows() else f'cmd /c "{full}"',
            cwd=os.getcwd(),
            timeout=120,
        )
        return ToolResult(
            success=(ec == 0 and not timed_out),
            output=output,
            duration=time.time() - t0,
            tool=self.name,
            args=kwargs,
            cancelled=timed_out,
        )


class ShellTools:
    """Convenience access to shell tools."""

    def __init__(self):
        self.cd = CdTool()
        self.command = ExecuteCommandTool()
        self.file = ExecuteFileTool()

    def get_all(self) -> list[BaseTool]:
        return [self.cd, self.command, self.file]
