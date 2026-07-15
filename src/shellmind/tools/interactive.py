"""
Interactive shell session management for ShellMind.

Allows starting a long-running shell session, sending commands to it,
and reading output. Sessions are managed per-instance (no globals).
"""

import os
import subprocess
import time
from typing import Any, Optional

from shellmind.tools.base import BaseTool, ToolResult
from shellmind.platform import is_windows


class ShellSession:
    """A persistent shell session that can receive commands incrementally."""

    def __init__(self, shell: Optional[str] = None):
        if not shell:
            shell = "cmd.exe" if is_windows() else "bash"
        self.shell = shell
        self.proc: Optional[subprocess.Popen] = None

    def start(self) -> None:
        """Start the shell process if not already running."""
        if self.proc and self.proc.poll() is None:
            return  # Already running
        self.proc = subprocess.Popen(
            [self.shell],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

    def send(self, command: str, timeout: int = 30) -> str:
        """Send a command and return the output."""
        self.start()

        self.proc.stdin.write(command + "\n")  # type: ignore[union-attr]
        self.proc.stdin.flush()  # type: ignore[union-attr]

        # Read output until timeout
        output_lines = []
        deadline = time.time() + timeout
        while time.time() < deadline:
            # Check if process is still alive
            if self.proc.poll() is not None:
                break
            try:
                line = self.proc.stdout.readline()  # type: ignore[union-attr]
                if not line:
                    break
                output_lines.append(line.rstrip())
            except (ValueError, OSError):
                break

        return "\n".join(output_lines)

    def close(self) -> None:
        """Terminate the shell session."""
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
            except Exception:
                pass
        self.proc = None

    @property
    def is_alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None


class ShellSendTool(BaseTool):
    """Send a command to a persistent interactive shell session."""

    def __init__(self, session: Optional[ShellSession] = None):
        super().__init__()
        self._session = session

    @property
    def name(self) -> str:
        return "shell_send"

    @property
    def description(self) -> str:
        return "Send a command to a persistent shell session. Args: `command`"

    def set_session(self, session: ShellSession) -> None:
        """Set the session instance. Called by the agent."""
        self._session = session

    @property
    def session(self) -> ShellSession:
        if self._session is None:
            self._session = ShellSession()
        return self._session

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        command = kwargs.get("command", "")
        if not command:
            return ToolResult(False, "No command provided", 0, self.name, kwargs)

        output = self.session.send(command, timeout=kwargs.get("timeout", 30))
        return ToolResult(True, output, time.time() - t0, self.name, kwargs)


class ShellCloseTool(BaseTool):
    """Close the persistent interactive shell session."""

    def __init__(self, session: Optional[ShellSession] = None):
        super().__init__()
        self._session = session

    @property
    def name(self) -> str:
        return "shell_close"

    @property
    def description(self) -> str:
        return "Close the persistent interactive shell session."

    def set_session(self, session: ShellSession) -> None:
        """Set the session instance. Called by the agent."""
        self._session = session

    def execute(self, **kwargs: Any) -> ToolResult:
        t0 = time.time()
        if self._session:
            self._session.close()
        return ToolResult(True, "Shell session closed", time.time() - t0, self.name, kwargs)


class InteractiveTools:
    """Convenience access to interactive shell tools with a shared session."""

    def __init__(self):
        self._session = ShellSession()
        self.send = ShellSendTool(session=self._session)
        self.close = ShellCloseTool(session=self._session)

    def get_all(self) -> list[BaseTool]:
        return [self.send, self.close]

    def close_session(self) -> None:
        """Clean up the shell session."""
        self._session.close()
