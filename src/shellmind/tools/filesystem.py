"""
File system tools for ShellMind.

Provides read, write, edit, and search operations on files.
Write and edit operations create undo backups automatically.
"""

import os
import subprocess
import time
from typing import Any

from shellmind.tools.base import BaseTool, ToolResult
from shellmind.tools.undo import backup_before_write
from shellmind.platform import is_windows


class ReadFileTool(BaseTool):
    """Read a file from disk."""

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read a file's contents."

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        if not path:
            return ToolResult(False, "No path provided", 0, self.name, kwargs)

        t0 = time.time()
        full = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)

        try:
            with open(full, encoding="utf-8") as f:
                content = f.read()
            return ToolResult(True, content, time.time() - t0, self.name, kwargs)
        except Exception as exc:
            return ToolResult(False, str(exc), time.time() - t0, self.name, kwargs)


class WriteFileTool(BaseTool):
    """Create or overwrite a file (with undo backup)."""

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Create or overwrite a file with the given content."

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        if not path:
            return ToolResult(False, "No path provided", 0, self.name, kwargs)

        t0 = time.time()
        full = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)

        # Create undo backup before overwriting
        backup_before_write(full)

        try:
            os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(content)
            return ToolResult(
                True,
                f"Written {len(content)} bytes to {os.path.basename(path)}",
                time.time() - t0,
                self.name,
                kwargs,
            )
        except Exception as exc:
            return ToolResult(False, str(exc), time.time() - t0, self.name, kwargs)


class EditFileTool(BaseTool):
    """Make targeted string replacements in a file (with undo backup)."""

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return "Replace text in a file. Args: `path`, `old_string`, `new_string`"

    def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        old_string = kwargs.get("old_string", "")
        new_string = kwargs.get("new_string", "")
        if not path or not old_string:
            return ToolResult(
                False, "Path and old_string are required", 0, self.name, kwargs,
            )

        t0 = time.time()
        full = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)

        try:
            with open(full, encoding="utf-8") as f:
                content = f.read()

            if old_string not in content:
                return ToolResult(
                    False,
                    f"String not found in {os.path.basename(path)}",
                    time.time() - t0,
                    self.name,
                    kwargs,
                )

            # Create undo backup before editing
            backup_before_write(full)

            new_content = content.replace(old_string, new_string, 1)
            with open(full, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                True,
                "Replaced 1 occurrence",
                time.time() - t0,
                self.name,
                kwargs,
            )
        except Exception as exc:
            return ToolResult(False, str(exc), time.time() - t0, self.name, kwargs)


class SearchCodeTool(BaseTool):
    """Search for patterns in files using ripgrep or fallback grep."""

    @property
    def name(self) -> str:
        return "search_code"

    @property
    def description(self) -> str:
        return "Search for a pattern in files (uses ripgrep or grep fallback)."

    def execute(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs.get("pattern", "")
        search_path = kwargs.get("path", ".")
        if not pattern:
            return ToolResult(False, "No pattern provided", 0, self.name, kwargs)

        t0 = time.time()
        full_path = (
            search_path
            if os.path.isabs(search_path)
            else os.path.join(os.getcwd(), search_path)
        )

        # Try ripgrep first
        result = self._try_rg(pattern, full_path)
        if result is not None:
            return result

        return self._try_fallback(pattern, full_path, t0)

    def _try_rg(self, pattern: str, path: str) -> ToolResult | None:
        try:
            result = subprocess.run(
                ["rg", "-n", pattern, path],
                capture_output=True, text=True, timeout=30,
            )
            output = result.stdout or result.stderr or "(no matches)"
            ok = result.returncode in (0, 1)
            return ToolResult(ok, output.strip(), 0, self.name, {})
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def _try_fallback(self, pattern: str, path: str, t0: float) -> ToolResult:
        try:
            if is_windows():
                result = subprocess.run(
                    ["findstr", "/s", "/n", pattern, f"{path}\\*"],
                    capture_output=True, text=True, timeout=30,
                )
            else:
                result = subprocess.run(
                    ["grep", "-rn", pattern, path],
                    capture_output=True, text=True, timeout=30,
                )
            output = result.stdout or result.stderr or "(no matches)"
            ok = result.returncode in (0, 1)
            return ToolResult(
                ok, output.strip(), time.time() - t0, self.name,
                {"pattern": pattern, "path": path},
            )
        except Exception as exc:
            return ToolResult(
                False, str(exc), time.time() - t0, self.name,
                {"pattern": pattern, "path": path},
            )


class FileSystemTools:
    """Convenience access to all filesystem tools."""

    def __init__(self):
        self.read = ReadFileTool()
        self.write = WriteFileTool()
        self.edit = EditFileTool()
        self.search = SearchCodeTool()

    def get_all(self) -> list[BaseTool]:
        return [self.read, self.write, self.edit, self.search]
