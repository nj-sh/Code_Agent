"""
Tests for ShellMind's memory persistence.
"""

import json

from shellmind.memory import Memory


class TestMemory:
    """Test Memory class functionality."""

    def test_load_exists(self, memory: Memory, memory_file):
        """Test loading an existing memory file."""
        assert memory.model == "test-model"
        assert memory.last_task == ""
        assert memory.last_summary == ""
        assert memory.history == []

    def test_save_and_reload(self, memory: Memory):
        """Test saving and reloading memory."""
        memory.model = "new-model"
        memory.last_task = "test task"
        memory.last_summary = "test summary"
        memory.add_message("user", "hello")
        memory.save()

        # Create a new instance reading the same file
        memory2 = Memory(memory.path)
        assert memory2.model == "new-model"
        assert memory2.last_task == "test task"
        assert memory2.last_summary == "test summary"
        assert len(memory2.history) >= 1

    def test_history_trimming(self, memory: Memory):
        """Test that history gets trimmed to MAX_HISTORY."""
        max_hist = 80
        for i in range(max_hist + 20):
            memory.add_message("user", f"msg {i}")
            memory.add_message("assistant", f"resp {i}")

        assert len(memory.history) <= max_hist * 2  # user + assistant per turn

    def test_clear_history(self, memory: Memory):
        """Test clearing history preserves other state."""
        memory.model = "my-model"
        memory.add_message("user", "hello")
        memory.clear_history()

        assert memory.history == []
        assert memory.model == "my-model"  # Other state preserved

    def test_defaults_on_missing_file(self, temp_dir):
        """Test creating memory with a non-existent file."""
        path = temp_dir / "nonexistent" / "memory.json"
        mem = Memory(path)
        assert mem.model == "qwen2.5-coder:3b"  # default from config
        assert mem.history == []

    def test_to_dict(self, memory: Memory):
        """Test the to_dict method."""
        memory.model = "test"
        d = memory.to_dict()
        assert isinstance(d, dict)
        assert d["model"] == "test"
        assert "history" in d
