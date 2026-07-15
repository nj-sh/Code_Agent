"""
Simple config parser for ShellMind user configuration.

Reads ~/.config/shellmind/config.toml (or config.json) for user preferences.
Uses pure Python — no TOML library dependency.

Supports: strings, numbers, booleans, lists, and nested sections.
"""

import json
import os
from pathlib import Path
from typing import Any

from shellmind.config import get_config_dir


def _parse_toml(text: str) -> dict[str, Any]:
    """Parse a minimal TOML-like format into a dict.

    Supports:
    - key = "value" (strings)
    - key = 123 (integers)
    - key = true/false (booleans)
    - [section] (sections)
    - # comments
    """
    result: dict[str, Any] = {}
    current_section = result
    current_key: str | None = None

    for line in text.split("\n"):
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Section headers: [section] or [section.subsection]
        if line.startswith("[") and line.endswith("]"):
            section_path = line[1:-1].strip().split(".")
            current_section = result
            for part in section_path:
                part = part.strip()
                if part not in current_section:
                    current_section[part] = {}
                current_section = current_section[part]
            continue

        # Key-value pairs
        if "=" in line:
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()

            # Parse value
            if value.startswith('"') and value.endswith('"'):
                parsed = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                parsed = value[1:-1]
            elif value.lower() == "true":
                parsed = True
            elif value.lower() == "false":
                parsed = False
            elif value.isdigit():
                parsed = int(value)
            elif value.replace(".", "").isdigit() and value.count(".") == 1:
                parsed = float(value)
            elif value.startswith("[") and value.endswith("]"):
                # Simple list parsing: ["a", "b", "c"]
                items = value[1:-1].split(",")
                parsed = []
                for item in items:
                    item = item.strip()
                    if item.startswith('"') and item.endswith('"'):
                        parsed.append(item[1:-1])
                    elif item.startswith("'") and item.endswith("'"):
                        parsed.append(item[1:-1])
                    else:
                        parsed.append(item)
            else:
                parsed = value

            current_section[key] = parsed

    return result


def load_config() -> dict[str, Any]:
    """Load user configuration from disk.

    Tries (in order):
    1. config.toml (preferred)
    2. config.json (legacy)
    Returns defaults if neither exists.
    """
    config_dir = get_config_dir()
    toml_path = config_dir / "config.toml"
    json_path = config_dir / "config.json"

    defaults = {
        "model": "qwen2.5-coder:3b",
        "provider": "auto",
        "theme": "dark",
        "mode": "auto",
        "verbose": True,
        "max_history": 80,
        "timeout": 120,
    }

    if toml_path.exists():
        try:
            with open(toml_path, encoding="utf-8") as f:
                parsed = _parse_toml(f.read())
            # Merge with defaults
            merged = dict(defaults)
            merged.update(parsed)
            return merged
        except Exception:
            return defaults

    if json_path.exists():
        try:
            with open(json_path, encoding="utf-8") as f:
                loaded = json.load(f)
            merged = dict(defaults)
            merged.update(loaded)
            return merged
        except Exception:
            return defaults

    return defaults


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to config.json."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "config.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
    except Exception:
        pass  # Best-effort save


def get_config_value(key: str, default: Any = None) -> Any:
    """Get a single config value with a fallback default."""
    return load_config().get(key, default)
