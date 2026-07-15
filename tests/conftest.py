"""
Shared test fixtures for ShellMind tests.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator

# Ensure the src directory is on the path so tests can import shellmind
_src = Path(__file__).parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

import pytest

from shellmind.memory import Memory


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as d:
        old_cwd = os.getcwd()
        os.chdir(d)
        yield Path(d)
        os.chdir(old_cwd)


@pytest.fixture
def memory_file(temp_dir: Path) -> Path:
    """Create a temporary memory file."""
    path = temp_dir / "memory.json"
    data = {
        "model": "test-model",
        "system_prompt": "",
        "last_task": "",
        "last_summary": "",
        "history": [],
    }
    with open(path, "w") as f:
        json.dump(data, f)
    return path


@pytest.fixture
def memory(memory_file: Path) -> Memory:
    """Create a Memory instance backed by a temp file."""
    return Memory(memory_file)
