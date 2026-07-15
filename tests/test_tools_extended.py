"""
Extended tests for ShellMind Phase 2 — CdTool, ToolRegistry, ProgressTracker.
"""

import os
import tempfile

from shellmind.tools.shell import CdTool, ShellTools
from shellmind.tools.registry import ToolRegistry
from shellmind.ui.display import ProgressTracker, Display
from shellmind.ui.theme import Theme, get_active, set_active


class TestCdTool:
    """Test the CdTool directory changing."""

    def setup_method(self):
        self.tool = CdTool()

    def test_cd_to_temp_dir(self):
        with tempfile.TemporaryDirectory() as d:
            original = os.getcwd()
            result = self.tool.execute(path=d)
            assert result.success
            assert os.getcwd() == os.path.abspath(d)
            os.chdir(original)

    def test_cd_nonexistent(self):
        result = self.tool.execute(path="/nonexistent_path_xyz123/foo")
        assert not result.success
        assert "not found" in result.output

    def test_cd_no_path(self):
        result = self.tool.execute(path="")
        assert not result.success


class TestToolRegistry:
    """Test the ToolRegistry wiring."""

    def test_register_and_dispatch(self):
        registry = ToolRegistry()
        shell = ShellTools()
        for tool in shell.get_all():
            registry.register(tool)

        tools = registry.list_tools()
        assert "execute_command" in tools
        assert "execute_file" in tools
        assert "cd" in tools

        # Test dispatch success
        result = registry.dispatch("execute_command", command="echo hello")
        assert result is not None

        # Test dispatch unknown
        result = registry.dispatch("nonexistent_tool")
        assert result is None

    def test_get_descriptions(self):
        registry = ToolRegistry()
        shell = ShellTools()
        for tool in shell.get_all():
            registry.register(tool)
        descs = registry.get_descriptions()
        assert "execute_command" in descs
        assert descs["execute_command"] != ""


class TestProgressTracker:
    """Test the ProgressTracker state machine."""

    def setup_method(self):
        self.tracker = ProgressTracker()

    def test_initial_state(self):
        assert not self.tracker.is_active
        assert self.tracker._steps == []

    def test_set_plan(self):
        self.tracker.set_plan(["Step 1", "Step 2", "Step 3"])
        assert self.tracker.is_active
        assert self.tracker._total_steps == 3
        assert len(self.tracker._steps) == 3
        assert self.tracker._steps[0]["status"] == "todo"
        assert self.tracker._steps[0]["label"] == "Step 1"

    def test_start_and_complete(self):
        self.tracker.set_plan(["Step A", "Step B"])
        self.tracker.start_step(0, "Running A")
        assert self.tracker._steps[0]["status"] == "doing"
        assert self.tracker._current_step == 0

        self.tracker.complete_step(0, success=True)
        assert self.tracker._steps[0]["status"] == "done"

        self.tracker.start_step(1, "Running B")
        assert self.tracker._steps[1]["status"] == "doing"

        self.tracker.complete_step(1, success=False)
        assert self.tracker._steps[1]["status"] == "failed"

    def test_reset(self):
        self.tracker.set_plan(["Step 1"])
        self.tracker.start_step(0)
        self.tracker.reset()
        assert not self.tracker.is_active
        assert self.tracker._steps == []


class TestTheme:
    """Test theme switching."""

    def test_dark_theme(self):
        theme = Theme.dark()
        assert theme.name == "dark"
        assert theme.accent == "\033[38;5;214m"  # Orange

    def test_light_theme(self):
        theme = Theme.light()
        assert theme.name == "light"
        assert theme.accent == "\033[34m"  # Blue

    def test_from_name(self):
        dark = Theme.from_name("dark")
        assert dark.name == "dark"
        light = Theme.from_name("light")
        assert light.name == "light"
        # Unknown falls back to dark
        unknown = Theme.from_name("unknown")
        assert unknown.name == "dark"

    def test_set_active(self):
        original = get_active().name
        set_active("light")
        assert get_active().name == "light"
        set_active("dark")
        assert get_active().name == "dark"
        # Restore
        set_active(original)
