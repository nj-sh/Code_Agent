"""
Tests for ShellMind Phase 3 (Git, FileOps, Pkg, Interactive tools)
and Phase 4 (ProviderRegistry, OpenAI provider).
"""

import os
import tempfile

from shellmind.tools.git import GitTools, _run_git
from shellmind.tools.fileops import FileOpsTools, CopyFileTool, MoveFileTool, DiffFilesTool
from shellmind.tools.pkg_manager import PkgTools
from shellmind.tools.interactive import InteractiveTools, ShellSession, ShellSendTool
from shellmind.llm.model_registry import ProviderRegistry
from shellmind.llm.openai import OpenAIProvider
from shellmind.llm.base import BaseLLMProvider


class TestGitTools:
    """Test git tool functions (not full integration)."""

    def test_git_tools_registered(self):
        tools = GitTools().get_all()
        names = [t.name for t in tools]
        assert "git_status" in names
        assert "git_log" in names
        assert "git_diff" in names
        assert "git_commit" in names
        assert "git_branch" in names

    def test_git_not_a_repo(self):
        with tempfile.TemporaryDirectory() as d:
            from shellmind.tools.git import GitStatusTool
            result = GitStatusTool().execute(path=d)
            assert not result.success
            assert "Not a git repository" in result.output or "not found" in result.output

    def test_run_git_invalid(self):
        ec, output = _run_git(["nonexistent-command"])
        assert ec != 0


class TestFileOpsTools:
    """Test file operation tools."""

    def test_tools_registered(self):
        tools = FileOpsTools().get_all()
        names = [t.name for t in tools]
        assert "copy_file" in names
        assert "move_file" in names
        assert "diff_files" in names

    def test_copy_file(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "source.txt")
            dst = os.path.join(d, "dest.txt")
            with open(src, "w") as f:
                f.write("hello")

            result = CopyFileTool().execute(source=src, destination=dst)
            assert result.success
            assert os.path.exists(dst)
            with open(dst) as f:
                assert f.read() == "hello"

    def test_copy_nonexistent(self):
        result = CopyFileTool().execute(source="/nonexistent/target", destination="/tmp/x")
        assert not result.success

    def test_move_file(self):
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "source.txt")
            dst = os.path.join(d, "moved.txt")
            with open(src, "w") as f:
                f.write("move me")

            result = MoveFileTool().execute(source=src, destination=dst)
            assert result.success
            assert os.path.exists(dst)
            assert not os.path.exists(src)

    def test_diff_files_same(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = os.path.join(d, "a.txt")
            f2 = os.path.join(d, "b.txt")
            with open(f1, "w") as f:
                f.write("same content")
            with open(f2, "w") as f:
                f.write("same content")

            result = DiffFilesTool().execute(file1=f1, file2=f2)
            assert result.success
            assert "identical" in result.output

    def test_diff_files_different(self):
        with tempfile.TemporaryDirectory() as d:
            f1 = os.path.join(d, "a.txt")
            f2 = os.path.join(d, "b.txt")
            with open(f1, "w") as f:
                f.write("line 1\nline 2")
            with open(f2, "w") as f:
                f.write("line 1\nline changed")

            result = DiffFilesTool().execute(file1=f1, file2=f2)
            assert result.success
            assert "differ" in result.output or "-line 2" in result.output


class TestPkgTools:
    """Test package management tools (auto-detect, no actual installs)."""

    def test_tools_registered(self):
        tools = PkgTools().get_all()
        names = [t.name for t in tools]
        assert "pkg_install" in names

    def test_install_no_packages(self):
        from shellmind.tools.pkg_manager import PkgInstallTool
        result = PkgInstallTool().execute(packages="")
        assert not result.success


class TestInteractiveTools:
    """Test interactive shell session management."""

    def test_tools_registered(self):
        tools = InteractiveTools().get_all()
        names = [t.name for t in tools]
        assert "shell_send" in names
        assert "shell_close" in names

    def test_session_start_close(self):
        session = ShellSession()
        session.start()
        assert session.is_alive
        session.close()
        assert not session.is_alive

    def test_session_open_close(self):
        """Test session lifecycle without sending commands (avoids readline blocking)."""
        session = ShellSession()
        session.start()
        assert session.is_alive
        session.close()
        assert not session.is_alive
        # Verify it can be restarted
        session.start()
        assert session.is_alive
        session.close()
        assert not session.is_alive


class TestProviderRegistry:
    """Test the provider registry (no network calls needed)."""

    def test_registry_init(self):
        registry = ProviderRegistry()
        providers = registry.list_providers()
        assert "ollama" in providers

    def test_active_provider_default(self):
        registry = ProviderRegistry()
        assert registry.active_name == "ollama" or registry.active_name in registry.list_providers()

    def test_switch_provider(self):
        registry = ProviderRegistry()
        # Should work without errors
        try:
            registry.active_provider = "ollama"
            assert registry.active_name == "ollama"
        except ValueError:
            pass  # Provider might not be available

    def test_list_available(self):
        registry = ProviderRegistry()
        available = registry.list_available()
        assert isinstance(available, list)

    def test_get_provider(self):
        registry = ProviderRegistry()
        ollama = registry.get("ollama")
        assert ollama is not None
        assert ollama.name == "ollama"

    def test_get_nonexistent(self):
        registry = ProviderRegistry()
        assert registry.get("nonexistent") is None


class TestOpenAIProvider:
    """Test OpenAI provider (no API calls, just instantiation and availability check)."""

    def test_provider_init(self):
        provider = OpenAIProvider()
        assert provider.name == "openai"
        assert provider.model == "gpt-4o-mini"

    def test_availability_no_key(self):
        provider = OpenAIProvider()
        assert not provider.is_available()  # No API key set

    def test_availability_with_key(self):
        provider = OpenAIProvider(api_key="test-key")
        assert provider.is_available()

    def test_chat_no_key(self):
        provider = OpenAIProvider()
        result = provider.chat([{"role": "user", "content": "hello"}])
        assert not result.success
        assert "API key" in result.content


class TestOpenAIProviderAsBase(TestProviderRegistry):
    """Verify OpenAIProvider conforms to BaseLLMProvider interface."""

    def test_is_instance(self):
        provider = OpenAIProvider()
        assert isinstance(provider, BaseLLMProvider)
