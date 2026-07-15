"""
Git integration tools for ShellMind.

Provides git_status, git_log, git_diff, git_commit, git_branch tools
that wrap common git commands using subprocess with argument lists
(avoiding shell injection).
"""

import os
import subprocess
import time
from typing import Any

from shellmind.tools.base import BaseTool, ToolResult


def _run_git(args: list[str], cwd: str | None = None, timeout: int = 30) -> tuple[int, str]:
    """Run a git command safely with argument list (no shell)."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or os.getcwd(),
        )
        output = result.stdout or result.stderr
        return result.returncode, output.strip()
    except FileNotFoundError:
        return -1, "git not found — is Git installed?"
    except subprocess.TimeoutExpired:
        return -1, "[timeout] Git command timed out"
    except Exception as exc:
        return -1, str(exc)


class GitStatusTool(BaseTool):
    """Show the current git working tree status."""

    @property
    def name(self) -> str:
        return "git_status"

    @property
    def description(self) -> str:
        return "Show git working tree status (modified, staged, untracked files)."

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        path = kwargs.get("path", os.getcwd())

        # Check if it's a git repo
        ec, _ = _run_git(["rev-parse", "--git-dir"], cwd=path)
        if ec != 0:
            return ToolResult(
                False, "Not a git repository",
                time.time() - t0, self.name, kwargs,
            )

        # Get branch
        _, branch_out = _run_git(["branch", "--show-current"], cwd=path)
        branch = branch_out or "detached HEAD"

        # Get status
        ec, status_out = _run_git(["status", "--short"], cwd=path)
        if ec != 0:
            return ToolResult(False, status_out, time.time() - t0, self.name, kwargs)

        result = f"On branch: {branch}\n{status_out}" if status_out else f"On branch: {branch}\n(clean working tree)"
        return ToolResult(True, result, time.time() - t0, self.name, kwargs)


class GitLogTool(BaseTool):
    """Show recent git commit history."""

    @property
    def name(self) -> str:
        return "git_log"

    @property
    def description(self) -> str:
        return "Show recent git commit history. Args: `count` (default 10)"

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        count = str(kwargs.get("count", 10))
        path = kwargs.get("path", os.getcwd())

        ec, output = _run_git(
            ["log", "--oneline", f"-{count}", "--no-color"],
            cwd=path,
        )
        if ec != 0:
            return ToolResult(False, output or "Git log failed", time.time() - t0, self.name, kwargs)
        return ToolResult(True, output or "(no commits)", time.time() - t0, self.name, kwargs)


class GitDiffTool(BaseTool):
    """Show git diff for unstaged or staged changes."""

    @property
    def name(self) -> str:
        return "git_diff"

    @property
    def description(self) -> str:
        return "Show git diff. Args: `staged` (bool, default False), `path` (optional file path)"

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        staged = kwargs.get("staged", False)
        file_path = kwargs.get("path", "")
        path = kwargs.get("cwd", os.getcwd())

        args = ["diff", "--no-color"]
        if staged:
            args.append("--cached")
        if file_path:
            args.extend(["--", file_path])

        ec, output = _run_git(args, cwd=path)
        if ec != 0:
            return ToolResult(False, output or "Git diff failed", time.time() - t0, self.name, kwargs)
        return ToolResult(True, output or "(no changes)", time.time() - t0, self.name, kwargs)


class GitCommitTool(BaseTool):
    """Create a git commit with a message (safe — no shell injection)."""

    @property
    def name(self) -> str:
        return "git_commit"

    @property
    def description(self) -> str:
        return "Create a git commit. Args: `message` (required), `add_all` (bool, default True)"

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        message = kwargs.get("message", "")
        add_all = kwargs.get("add_all", True)
        path = kwargs.get("path", os.getcwd())

        if not message:
            return ToolResult(False, "Commit message is required", 0, self.name, kwargs)

        if add_all:
            ec, out = _run_git(["add", "-A"], cwd=path)
            if ec != 0:
                return ToolResult(False, f"git add failed: {out}", time.time() - t0, self.name, kwargs)

        # Safe: pass message as separate argument, not via shell
        ec, output = _run_git(["commit", "-m", message], cwd=path)
        if ec != 0:
            return ToolResult(False, output or "Commit failed", time.time() - t0, self.name, kwargs)
        return ToolResult(True, output, time.time() - t0, self.name, kwargs)


class GitBranchTool(BaseTool):
    """List or create git branches (safe — no shell injection)."""

    @property
    def name(self) -> str:
        return "git_branch"

    @property
    def description(self) -> str:
        return "List or create git branches. Args: `create` (branch name), `delete` (branch name)"

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        create = kwargs.get("create", "")
        delete = kwargs.get("delete", "")
        path = kwargs.get("path", os.getcwd())

        if create:
            ec, output = _run_git(["branch", create], cwd=path)
            if ec != 0:
                return ToolResult(False, output or f"Failed to create branch", time.time() - t0, self.name, kwargs)
            return ToolResult(True, f"Created branch '{create}'\n{output}", time.time() - t0, self.name, kwargs)

        if delete:
            ec, output = _run_git(["branch", "-d", delete], cwd=path)
            if ec != 0:
                return ToolResult(False, output or f"Failed to delete branch", time.time() - t0, self.name, kwargs)
            return ToolResult(True, f"Deleted branch '{delete}'\n{output}", time.time() - t0, self.name, kwargs)

        ec, output = _run_git(["branch"], cwd=path)
        if ec != 0:
            return ToolResult(False, output or "Git branch failed", time.time() - t0, self.name, kwargs)
        return ToolResult(True, output, time.time() - t0, self.name, kwargs)


class GitTools:
    """Convenience access to all git tools."""

    def __init__(self):
        self.status = GitStatusTool()
        self.log = GitLogTool()
        self.diff = GitDiffTool()
        self.commit = GitCommitTool()
        self.branch = GitBranchTool()

    def get_all(self) -> list[BaseTool]:
        return [self.status, self.log, self.diff, self.commit, self.branch]
