"""
File operation tools for ShellMind.

Provides copy, move, and diff operations on files and directories.
"""

import os
import shutil
import time
from typing import Any

from shellmind.tools.base import BaseTool, ToolResult
from shellmind.platform import run_command


class CopyFileTool(BaseTool):
    """Copy a file or directory."""

    @property
    def name(self) -> str:
        return "copy_file"

    @property
    def description(self) -> str:
        return "Copy a file or directory. Args: `source`, `destination`"

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        source = kwargs.get("source", "")
        dest = kwargs.get("destination", "") or kwargs.get("dest", "")

        if not source or not dest:
            return ToolResult(False, "Both 'source' and 'destination' are required", 0, self.name, kwargs)

        src_path = source if os.path.isabs(source) else os.path.join(os.getcwd(), source)
        dst_path = dest if os.path.isabs(dest) else os.path.join(os.getcwd(), dest)

        if not os.path.exists(src_path):
            return ToolResult(False, f"Source not found: {source}", time.time() - t0, self.name, kwargs)

        try:
            if os.path.isdir(src_path):
                shutil.copytree(src_path, dst_path)
                return ToolResult(True, f"Copied directory '{source}' -> '{dest}'", time.time() - t0, self.name, kwargs)
            else:
                os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
                shutil.copy2(src_path, dst_path)
                size = os.path.getsize(dst_path)
                return ToolResult(True, f"Copied '{source}' -> '{dest}' ({size} bytes)", time.time() - t0, self.name, kwargs)
        except Exception as exc:
            return ToolResult(False, f"Copy failed: {exc}", time.time() - t0, self.name, kwargs)


class MoveFileTool(BaseTool):
    """Move or rename a file or directory."""

    @property
    def name(self) -> str:
        return "move_file"

    @property
    def description(self) -> str:
        return "Move or rename a file or directory. Args: `source`, `destination`"

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        source = kwargs.get("source", "")
        dest = kwargs.get("destination", "") or kwargs.get("dest", "")

        if not source or not dest:
            return ToolResult(False, "Both 'source' and 'destination' are required", 0, self.name, kwargs)

        src_path = source if os.path.isabs(source) else os.path.join(os.getcwd(), source)
        dst_path = dest if os.path.isabs(dest) else os.path.join(os.getcwd(), dest)

        if not os.path.exists(src_path):
            return ToolResult(False, f"Source not found: {source}", time.time() - t0, self.name, kwargs)

        try:
            os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
            shutil.move(src_path, dst_path)
            return ToolResult(True, f"Moved '{source}' -> '{dest}'", time.time() - t0, self.name, kwargs)
        except Exception as exc:
            return ToolResult(False, f"Move failed: {exc}", time.time() - t0, self.name, kwargs)


class DiffFilesTool(BaseTool):
    """Show diff between two files."""

    @property
    def name(self) -> str:
        return "diff_files"

    @property
    def description(self) -> str:
        return "Show diff between two files. Args: `file1`, `file2`"

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        file1 = kwargs.get("file1", "")
        file2 = kwargs.get("file2", "")

        if not file1 or not file2:
            return ToolResult(False, "Both 'file1' and 'file2' are required", 0, self.name, kwargs)

        path1 = file1 if os.path.isabs(file1) else os.path.join(os.getcwd(), file1)
        path2 = file2 if os.path.isabs(file2) else os.path.join(os.getcwd(), file2)

        if not os.path.isfile(path1):
            return ToolResult(False, f"File not found: {file1}", time.time() - t0, self.name, kwargs)
        if not os.path.isfile(path2):
            return ToolResult(False, f"File not found: {file2}", time.time() - t0, self.name, kwargs)

        # Try diff, fall back to simple line comparison
        ec, output, _ = run_command(f'diff -u "{path1}" "{path2}"', cwd=os.getcwd(), timeout=30)
        if ec in (0, 1) and output:
            return ToolResult(True, output, time.time() - t0, self.name, kwargs)

        # Fallback: simple diff output
        try:
            with open(path1, encoding="utf-8") as f:
                lines1 = f.readlines()
            with open(path2, encoding="utf-8") as f:
                lines2 = f.readlines()

            if lines1 == lines2:
                return ToolResult(True, "(files are identical)", time.time() - t0, self.name, kwargs)

            # Show first few differing lines
            diff_lines = []
            max_lines = max(len(lines1), len(lines2))
            shown = 0
            for i in range(max_lines):
                l1 = lines1[i].rstrip() if i < len(lines1) else ""
                l2 = lines2[i].rstrip() if i < len(lines2) else ""
                if l1 != l2 and shown < 20:
                    diff_lines.append(f"-{l1}")
                    diff_lines.append(f"+{l2}")
                    shown += 1

            return ToolResult(True, f"Files differ ({max(len(lines1), len(lines2))} lines total).\n" + "\n".join(diff_lines[:40]), time.time() - t0, self.name, kwargs)
        except Exception as exc:
            return ToolResult(False, f"Diff failed: {exc}", time.time() - t0, self.name, kwargs)


class FileOpsTools:
    """Convenience access to all file operation tools."""

    def __init__(self):
        self.copy = CopyFileTool()
        self.move = MoveFileTool()
        self.diff = DiffFilesTool()

    def get_all(self) -> list[BaseTool]:
        return [self.copy, self.move, self.diff]
