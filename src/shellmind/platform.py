"""
Cross-platform utilities for ShellMind.

Handles platform detection, process management, path normalization,
and shell interaction across Windows, Linux, and macOS.
"""

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


def is_windows() -> bool:
    """Check if running on Windows."""
    return sys.platform == "win32" or os.name == "nt"


def is_unix() -> bool:
    """Check if running on a Unix-like system (Linux, macOS, WSL, etc.)."""
    return not is_windows()


def is_wsl() -> bool:
    """Check if running inside WSL (Windows Subsystem for Linux)."""
    if not is_unix():
        return False
    try:
        with open("/proc/version", encoding="ascii", errors="ignore") as f:
            return "microsoft" in f.read().lower() or "wsl" in f.read().lower()
    except FileNotFoundError:
        return False


def get_platform_label() -> str:
    """Get a human-readable platform label."""
    if is_wsl():
        return f"WSL ({sys.platform})"
    if is_windows():
        return f"Windows ({sys.platform})"
    return sys.platform


def get_shell() -> str:
    """Detect the current shell."""
    if is_windows():
        # Check for PowerShell, cmd, or Git Bash
        ps_parent = os.environ.get("PSModulePath", "")
        if ps_parent:
            return "powershell"
        # Check common env vars
        shell = os.environ.get("SHELL", "")
        if shell:
            return os.path.basename(shell)
        return "cmd"
    else:
        return os.path.basename(os.environ.get("SHELL", "bash"))


def normalize_path(path: str) -> str:
    """Normalize a path for the current platform.

    - On Windows: replace / with \\, handle C:/ style paths
    - On Unix: keep /, expand ~
    - Strips trailing slashes (except root)
    """
    path = os.path.expanduser(path)
    path = os.path.normpath(path)
    return path


def find_executable(name: str) -> Optional[str]:
    """Find an executable on PATH, cross-platform.

    Returns full path or None.
    """
    return shutil.which(name)


def get_config_dir() -> Path:
    """Get the platform-appropriate config directory."""
    if is_windows():
        base = os.environ.get("APPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Roaming"))
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
    return Path(base) / "shellmind"


def get_data_dir() -> Path:
    """Get the platform-appropriate data directory."""
    if is_windows():
        base = os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local"))
    else:
        base = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
    return Path(base) / "shellmind"


def get_desktop_path() -> Optional[Path]:
    """Get the user's Desktop directory path."""
    desktop = Path(os.path.expanduser("~/Desktop"))
    if desktop.exists():
        return desktop
    # Fallback for some Windows configurations
    alt = Path(os.path.expanduser("~")) / "OneDrive" / "Desktop"
    if alt.exists():
        return alt
    return None


# ─── Cross-Platform Process Management ──────────────────────────────────────


def get_process_group_flags() -> int:
    """Get the appropriate subprocess flags for process group creation.

    On Unix: use preexec_fn=os.setsid to create a new process group.
    On Windows: use CREATE_NEW_PROCESS_GROUP flag.
    """
    if is_windows():
        return subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    return 0  # Will use preexec_fn instead


def kill_process_group(proc: subprocess.Popen) -> None:
    """Kill an entire process group, cross-platform."""
    if proc.poll() is not None:
        return  # Already dead

    try:
        if is_windows():
            proc.kill()  # On Windows, just kill the process
        else:
            # Kill the process group
            pgid = os.getpgid(proc.pid) if hasattr(os, 'getpgid') else proc.pid
            os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        # Process may have already exited
        try:
            proc.kill()
        except Exception:
            pass


def run_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 120,
    env: Optional[dict[str, str]] = None,
) -> tuple[int, str, bool]:
    """Run a shell command and return (exit_code, output, timed_out).

    Cross-platform implementation that handles:
    - Unix: creates process group with os.setsid
    - Windows: uses CREATE_NEW_PROCESS_GROUP
    - Timeout: kills the entire process group
    """
    t0 = time.time()
    timed_out = False

    try:
        if is_windows():
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                env=env,
                creationflags=get_process_group_flags(),
            )
        else:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=cwd,
                env=env,
                preexec_fn=os.setsid,
            )

        try:
            output, _ = proc.communicate(timeout=timeout)
            exit_code = proc.returncode or 0
        except subprocess.TimeoutExpired:
            kill_process_group(proc)
            output = "[timeout] Command timed out after {}s".format(timeout)
            exit_code = -1
            timed_out = True

    except FileNotFoundError:
        output = f"[error] Command not found: {command}"
        exit_code = -1
    except Exception as exc:
        output = f"[error] {exc}"
        exit_code = -1

    return exit_code, output.strip(), timed_out


def run_command_streaming(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 120,
    on_line: Optional[callable] = None,
) -> tuple[int, str, bool]:
    """Run a command and stream output line-by-line via callback.

    Returns (exit_code, full_output, timed_out).
    """
    lines: list[str] = []
    timed_out = False

    try:
        if is_windows():
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=cwd,
                creationflags=get_process_group_flags(),
            )
        else:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=cwd,
                preexec_fn=os.setsid,
            )

        deadline = time.time() + timeout

        while True:
            line = proc.stdout.readline()  # type: ignore[union-attr]
            if not line and proc.poll() is not None:
                break
            if time.time() > deadline:
                kill_process_group(proc)
                timed_out = True
                break
            if line:
                lines.append(line.rstrip())
                if on_line:
                    on_line(line.rstrip())

        exit_code = proc.returncode or 0
        if timed_out:
            lines.append("[timeout] Command timed out after {}s".format(timeout))
            exit_code = -1

    except Exception as exc:
        output = f"[error] {exc}"
        return -1, output, False

    return exit_code, "\n".join(lines), timed_out
