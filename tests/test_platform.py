"""
Tests for ShellMind's cross-platform utilities.
"""

import os
import tempfile
from pathlib import Path

from shellmind.platform import (
    is_windows,
    is_unix,
    normalize_path,
    run_command,
)


class TestPlatformDetection:
    """Test platform detection functions."""

    def test_is_windows_or_unix(self):
        """Test that platform detection is consistent."""
        # They should be opposites
        assert is_windows() != is_unix()


class TestNormalizePath:
    """Test path normalization."""

    def test_expand_user(self):
        """Test that ~ gets expanded."""
        expanded = normalize_path("~/test")
        assert "~" not in expanded
        assert expanded.endswith("test")

    def test_normalize_relative(self):
        """Test normalizing relative paths."""
        result = normalize_path("./foo/bar/../baz")
        assert ".." not in result
        assert result.endswith("baz") or result.endswith("foo\\baz")

    def test_absolute_path(self):
        """Test that absolute paths remain absolute."""
        if is_windows():
            # Use a path that works on Windows
            result = normalize_path("C:\\Users\\test")
            assert result.startswith("C:\\") or result.startswith("c:\\")
        else:
            result = normalize_path("/usr/local")
            assert result.startswith("/")


class TestRunCommand:
    """Test shell command execution."""

    def test_echo(self):
        """Test running a simple echo command."""
        if is_windows():
            ec, output, timed_out = run_command("echo hello")
            assert ec == 0 or ec == 1  # echo in cmd is 0
        else:
            ec, output, timed_out = run_command("echo hello")
            assert ec == 0
            assert "hello" in output

    def test_failing_command(self):
        """Test a command that fails."""
        if is_windows():
            ec, output, timed_out = run_command("exit /b 1")
        else:
            ec, output, timed_out = run_command("false")
        assert ec != 0

    def test_timeout(self):
        """Test command timeout handling."""
        ec, output, timed_out = run_command(
            "sleep 5" if not is_windows() else "timeout /t 5 /nobreak",
            timeout=1,
        )
        # Should time out
        assert timed_out or ec != 0

    def test_cwd(self):
        """Test running a command in a specific directory."""
        with tempfile.TemporaryDirectory() as d:
            ec, output, timed_out = run_command(
                "pwd" if not is_windows() else "cd",
                cwd=d,
            )
            assert ec == 0
            # The output should contain the directory path
            assert os.path.basename(d) in output
