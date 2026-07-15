"""
Configuration constants and defaults for ShellMind.
"""

import os
from pathlib import Path

# ─── Version ──────────────────────────────────────────────────────────────────

VERSION = "5.0.0"

# ─── Ollama Defaults ──────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_API_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder:3b"

# ─── Agent Defaults ───────────────────────────────────────────────────────────

DEFAULT_MODE = "auto"  # auto or manual
COMMAND_TIMEOUT = 120
MAX_HISTORY = 80
LLM_TEMPERATURE = 0.1
LLM_TIMEOUT = 180
LLM_MAX_RETRIES = 3

# ─── File Paths ───────────────────────────────────────────────────────────────

def get_config_dir() -> Path:
    """Get the user-level config directory for ShellMind."""
    config_home = os.environ.get(
        "XDG_CONFIG_HOME",
        os.path.join(os.path.expanduser("~"), ".config"),
    )
    return Path(config_home) / "shellmind"


def get_data_dir() -> Path:
    """Get the user-level data directory for ShellMind."""
    data_home = os.environ.get(
        "XDG_DATA_HOME",
        os.path.join(os.path.expanduser("~"), ".local", "share"),
    )
    return Path(data_home) / "shellmind"


def get_memory_path() -> Path:
    """Get the path to the session memory file."""
    # Priority: config dir > legacy package dir
    config_mem = get_config_dir() / "memory.json"
    if config_mem.exists():
        return config_mem
    legacy = Path(__file__).parent.parent.parent / "memory.json"
    if legacy.exists():
        return legacy
    # Default to config dir
    return config_mem


def get_config_path() -> Path:
    """Get the path to the user config file."""
    return get_config_dir() / "config.json"


HOME = os.path.expanduser("~")

# ─── Display Width ────────────────────────────────────────────────────────────

import shutil

def get_terminal_width() -> int:
    """Get terminal width, respecting env var override."""
    try:
        return shutil.get_terminal_size((80, 24)).columns
    except Exception:
        return 80
