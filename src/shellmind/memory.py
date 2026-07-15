"""
Session memory persistence for ShellMind.

Stores conversation history, model selection, and last task state
in a JSON file that survives restarts.
"""

import json
from pathlib import Path
from typing import Any

from shellmind.config import DEFAULT_MODEL, MAX_HISTORY, get_memory_path, get_config_dir


class Memory:
    """Persistent session memory backed by a JSON file."""

    DEFAULTS: dict[str, Any] = {
        "model": DEFAULT_MODEL,
        "system_prompt": "",
        "last_task": "",
        "last_summary": "",
        "history": [],
    }

    def __init__(self, path: Path | None = None):
        self.path = path or get_memory_path()
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load memory from disk, creating defaults if missing."""
        try:
            if self.path.exists():
                with open(self.path, encoding="utf-8") as f:
                    self._data = json.load(f)
            else:
                self._data = dict(self.DEFAULTS)
                self.save()
        except (json.JSONDecodeError, OSError):
            self._data = dict(self.DEFAULTS)
            self.save()

        # Ensure all keys exist
        for k, v in self.DEFAULTS.items():
            self._data.setdefault(k, v)

    def save(self) -> None:
        """Persist memory to disk atomically."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            tmp.replace(self.path)
        except OSError:
            pass  # Best-effort persistence

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    @property
    def model(self) -> str:
        return self._data.get("model", DEFAULT_MODEL)

    @model.setter
    def model(self, value: str) -> None:
        self._data["model"] = value

    @property
    def history(self) -> list[dict]:
        return self._data.get("history", [])

    @history.setter
    def history(self, value: list[dict]) -> None:
        self._data["history"] = value[-MAX_HISTORY:]

    def add_message(self, role: str, content: str) -> None:
        """Add a message to history and trim if needed."""
        hist = self.history
        hist.append({"role": role, "content": content})
        self.history = hist  # uses setter which trims

    def clear_history(self) -> None:
        """Clear conversation history but keep other state."""
        self._data["history"] = []

    @property
    def last_task(self) -> str:
        return self._data.get("last_task", "")

    @last_task.setter
    def last_task(self, value: str) -> None:
        self._data["last_task"] = value[:100]

    @property
    def last_summary(self) -> str:
        return self._data.get("last_summary", "")

    @last_summary.setter
    def last_summary(self, value: str) -> None:
        self._data["last_summary"] = value

    def to_dict(self) -> dict:
        """Return a copy of the internal data."""
        return dict(self._data)
