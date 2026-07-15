"""
Package management tools for ShellMind.

Intelligently detects the language/framework and installs packages
using the appropriate package manager (pip, npm, cargo, etc.).
"""

import os
import re
import time
from typing import Any

from shellmind.tools.base import BaseTool, ToolResult
from shellmind.platform import run_command, find_executable


def _detect_package_managers(cwd: str) -> list[str]:
    """Detect which package managers are relevant based on project files."""
    managers = []
    files = set()

    try:
        files = set(os.listdir(cwd))
    except PermissionError:
        pass

    if "requirements.txt" in files or "setup.py" in files or "setup.cfg" in files or "pyproject.toml" in files:
        if find_executable("pip"):
            managers.append("pip")
    if "package.json" in files:
        if find_executable("npm"):
            managers.append("npm")
    if "Cargo.toml" in files:
        if find_executable("cargo"):
            managers.append("cargo")
    if "go.mod" in files:
        if find_executable("go"):
            managers.append("go")

    return managers


class PkgInstallTool(BaseTool):
    """Install packages using the appropriate package manager."""

    @property
    def name(self) -> str:
        return "pkg_install"

    @property
    def description(self) -> str:
        return "Install packages. Args: `packages` (str, space-separated), `manager` (optional: pip, npm, cargo, auto-detect)"

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        packages = kwargs.get("packages", "")
        manager = kwargs.get("manager", "auto")
        path = kwargs.get("path", os.getcwd())

        if not packages:
            return ToolResult(False, "No packages specified", 0, self.name, kwargs)

        if manager == "auto":
            detected = _detect_package_managers(path)
            if not detected:
                return ToolResult(
                    False,
                    "No supported package manager detected (checked: pip, npm, cargo, go). "
                    "Specify one with manager='pip' or manager='npm'.",
                    time.time() - t0, self.name, kwargs,
                )
            manager = detected[0]  # Use first detected

        cmds = {
            "pip": f"pip install {packages}",
            "npm": f"npm install {packages}",
            "cargo": f"cargo add {packages}",
            "go": f"go get {packages}",
        }

        cmd = cmds.get(manager)
        if not cmd:
            return ToolResult(
                False,
                f"Unknown package manager: {manager}. Supported: pip, npm, cargo, go",
                time.time() - t0, self.name, kwargs,
            )

        ec, output, timed_out = run_command(cmd, cwd=path, timeout=120)
        return ToolResult(
            success=(ec == 0 and not timed_out),
            output=output or f"Installed {packages} via {manager}",
            duration=time.time() - t0,
            tool=self.name,
            args=kwargs,
            cancelled=timed_out,
        )


class PkgTools:
    """Convenience access to package management tools."""

    def __init__(self):
        self.install = PkgInstallTool()

    def get_all(self) -> list[BaseTool]:
        return [self.install]
