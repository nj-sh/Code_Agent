"""
Tests for ShellMind's tool implementations.
"""

import os
import tempfile

from shellmind.tools.shell import ExecuteCommandTool, ExecuteFileTool
from shellmind.tools.filesystem import ReadFileTool, WriteFileTool, EditFileTool


class TestExecuteCommandTool:
    """Test the execute_command tool."""

    def setup_method(self):
        self.tool = ExecuteCommandTool()

    def test_echo(self):
        result = self.tool.execute(command="echo hello world")
        assert result.success
        assert "hello world" in result.output

    def test_failing_command(self):
        result = self.tool.execute(command="false" if os.name != "nt" else "exit /b 1")
        assert not result.success


class TestFileSystemTools:
    """Test file system operations."""

    def setup_method(self):
        self.read = ReadFileTool()
        self.write = WriteFileTool()
        self.edit = EditFileTool()

    def test_write_and_read(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.txt")
            result = self.write.execute(path=path, content="hello world")
            assert result.success
            assert "Written" in result.output

            result = self.read.execute(path=path)
            assert result.success
            assert result.output == "hello world"

    def test_edit(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.txt")
            self.write.execute(path=path, content="hello world foo")

            result = self.edit.execute(
                path=path,
                old_string="foo",
                new_string="bar",
            )
            assert result.success
            assert "Replaced" in result.output

            result = self.read.execute(path=path)
            assert result.output == "hello world bar"

    def test_edit_nonexistent_string(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "test.txt")
            self.write.execute(path=path, content="hello world")

            result = self.edit.execute(
                path=path,
                old_string="nonexistent",
                new_string="bar",
            )
            assert not result.success
            assert "not found" in result.output

    def test_read_nonexistent(self):
        result = self.read.execute(path="/nonexistent/path/file.txt")
        assert not result.success
