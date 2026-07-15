"""
Undo system for ShellMind.

Backs up files before write/edit operations and provides an undo tool
to restore them. Undo history is per-session (not persisted).
"""

import os
import shutil
import tempfile
import time
from typing import Any, Optional

from shellmind.tools.base import BaseTool, ToolResult


# In-memory undo stack: list of (file_path, backup_path)
_undo_stack: list[tuple[str, str]] = []


def backup_before_write(file_path: str) -> None:
    """Create a backup of a file before it's modified.

    Called by write_file and edit_file tools before making changes.
    Only backs up files that exist (not new files).
    """
    if not os.path.isfile(file_path):
        return  # New file, no need to backup

    # Create backup in temp directory
    backup_dir = os.path.join(tempfile.gettempdir(), "shellmind_undo")
    os.makedirs(backup_dir, exist_ok=True)

    backup_name = f"{os.path.basename(file_path)}.{int(time.time())}.bak"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        shutil.copy2(file_path, backup_path)
        _undo_stack.append((file_path, backup_path))
        # Keep stack limited to 50 entries
        if len(_undo_stack) > 50:
            _undo_stack.pop(0)
    except Exception:
        pass  # Best-effort backup


class UndoTool(BaseTool):
    """Undo the last file write/edit operation."""

    def __init__(self, undo_stack: Optional[list] = None):
        super().__init__()
        self._stack = undo_stack or _undo_stack

    @property
    def name(self) -> str:
        return "undo"

    @property
    def description(self) -> str:
        return "Undo the last file write/edit operation. Args: `count` (number of undos, default 1)"

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        count = kwargs.get("count", 1)

        if not self._stack:
            return ToolResult(False, "Nothing to undo", time.time() - t0, self.name, kwargs)

        restored = 0
        errors = []

        for _ in range(min(count, len(self._stack))):
            file_path, backup_path = self._stack.pop()
            if os.path.isfile(backup_path):
                try:
                    shutil.copy2(backup_path, file_path)
                    restored += 1
                except Exception as exc:
                    errors.append(f"Failed to restore {file_path}: {exc}")
            else:
                errors.append(f"Backup not found for {file_path}")

        results = [f"Restored {restored} file(s)"]
        if errors:
            results.extend(errors)

        return ToolResult(
            success=(restored > 0),
            output="\n".join(results),
            duration=time.time() - t0,
            tool=self.name,
            args=kwargs,
        )


class UndoTools:
    """Convenience access to undo tools."""

    def __init__(self):
        self.undo = UndoTool()

    def get_all(self) -> list[BaseTool]:
        return [self.undo]
