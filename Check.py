#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════╗
║    🔍 Code Agent — Pre-Flight Check             ║
╚══════════════════════════════════════════════════╝

Diagnoses issues before running Agent.py.
Checks Python, Ollama, model, tools, and permissions.
Asks Y/N on each failure so you can decide what to fix.

Usage:
    python3 Check.py
"""

import json
import os
import shutil
import struct
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ─── ANSI Colors ──────────────────────────────────────────────────────────────

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"

# ─── Config ───────────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434"
MEMORY_FILE = Path(__file__).parent / "memory.json"
MIN_PYTHON = (3, 8)

# ─── Results ──────────────────────────────────────────────────────────────────

passed = 0
failed = 0
skipped = 0


def ok(msg: str) -> None:
    global passed
    passed += 1
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg: str, hint: str = "") -> bool:
    """Report failure and ask Y/N. Returns True if user wants to continue."""
    global failed
    failed += 1
    print(f"  {RED}✗{RESET} {msg}")
    if hint:
        print(f"    {YELLOW}💡 {hint}{RESET}")
    while True:
        try:
            ans = input(f"    {YELLOW}Continue anyway? [y/N]: {RESET}").strip().lower()
            if ans in ("y", "yes"):
                print(f"    {DIM}→ Continuing...{RESET}")
                return True
            if ans in ("", "n", "no"):
                return False
        except (EOFError, KeyboardInterrupt):
            return False


def skip(msg: str) -> None:
    global skipped
    skipped += 1
    print(f"  {YELLOW}−{RESET} {msg}")


# ─── Header ───────────────────────────────────────────────────────────────────


def print_header() -> None:
    w = shutil.get_terminal_size((60, 20)).columns
    w = min(w, 66)
    print(f"\n{BOLD}{CYAN}╔{'═' * (w - 2)}╗{RESET}")
    title = "🔍 Code Agent — Pre-Flight Check"
    pad = (w - 2 - len(title)) // 2
    print(f"{BOLD}{CYAN}║{' ' * pad}{title}{' ' * (w - 2 - len(title) - pad)}║{RESET}")
    print(f"{BOLD}{CYAN}╚{'═' * (w - 2)}╝{RESET}")
    print()


# ─── Checks ────────────────────────────────────────────────────────────────────


def check_python() -> bool:
    """Check Python version is 3.8+."""
    v = sys.version_info
    ver_str = f"{v.major}.{v.minor}.{v.micro}"
    if (v.major, v.minor) >= MIN_PYTHON:
        ok(f"Python {ver_str} (≥ {MIN_PYTHON[0]}.{MIN_PYTHON[1]})")
        return True
    return fail(
        f"Python {ver_str} — need ≥ {MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
        "Install a newer Python from https://python.org",
    )


def check_ollama_installed() -> bool:
    """Check if the ollama binary is on PATH."""
    ollama_bin = shutil.which("ollama")
    if ollama_bin:
        try:
            ver = subprocess.run(
                ["ollama", "--version"],
                capture_output=True, text=True, timeout=10,
            )
            ver_out = ver.stdout.strip() or ver.stderr.strip() or "(unknown version)"
            ok(f"Ollama binary found — {ver_out}")
            return True
        except Exception as e:
            skip(f"Ollama binary found but version check failed: {e}")
            return True
    return fail(
        "Ollama not found on PATH",
        "Install: curl -fsSL https://ollama.com/install.sh | sh",
    )


def check_ollama_running() -> bool:
    """Check if Ollama API is reachable."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                ok("Ollama server running on localhost:11434")
                return True
            else:
                return fail(
                    f"Ollama responded with HTTP {resp.status}",
                    "Check: ollama serve",
                )
    except urllib.error.URLError as e:
        return fail(
            f"Ollama API unreachable — {e.reason}",
            "Start Ollama: ollama serve\n"
            "  Or install: curl -fsSL https://ollama.com/install.sh | sh",
        )
    except Exception as e:
        return fail(
            f"Ollama check failed: {e}",
            "Start Ollama: ollama serve",
        )


def check_model_available() -> bool:
    """Check if the default model (from memory.json) is pulled in Ollama."""
    model = "qwen2.5-coder:3b"  # default
    try:
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE) as f:
                mem = json.load(f)
            model = mem.get("model", model)
    except Exception:
        pass

    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m["name"] for m in data.get("models", [])]
    except Exception:
        skip("Could not list Ollama models (server may be down)")
        return True

    # Check exact match or partial match
    for m in models:
        if model in m or m in model:
            ok(f"Model '{model}' is available")
            return True

    return fail(
        f"Model '{model}' not found in Ollama",
        f"Pull it: ollama pull {model}\n"
        f"  List models: ollama list\n"
        f"  Switch model in Agent.py with :model <name>",
    )


def check_tools() -> bool:
    """Check essential CLI tools: rg (ripgrep) or grep fallback."""
    all_ok = True

    rg_path = shutil.which("rg")
    grep_path = shutil.which("grep")

    if rg_path:
        ok("ripgrep (rg) available — fast code search")
    elif grep_path:
        skip("ripgrep not found, falling back to grep (slower)")
    else:
        all_ok = fail(
            "Neither ripgrep (rg) nor grep found",
            "Install ripgrep: apt install ripgrep / brew install ripgrep",
        )

    # Check other useful tools
    for tool, label in [
        ("python3", "Python 3"),
        ("git", "Git"),
    ]:
        if shutil.which(tool):
            ok(f"{label} available")
        else:
            skip(f"{label} not found (optional)")

    return all_ok


def check_terminal() -> bool:
    """Check terminal capabilities."""
    try:
        cols = shutil.get_terminal_size((80, 24)).columns
        ok(f"Terminal width: {cols} columns")
        return True
    except Exception as e:
        skip(f"Could not detect terminal size: {e}")
        return True


def check_memory_file() -> bool:
    """Check memory.json exists and is writable."""
    try:
        if MEMORY_FILE.exists():
            ok(f"memory.json exists ({MEMORY_FILE.stat().st_size} bytes)")
        else:
            # Try to create it
            example = {
                "model": "qwen2.5-coder:3b",
                "system_prompt": "",
                "last_task": "",
                "last_summary": "",
                "history": [],
            }
            with open(MEMORY_FILE, "w") as f:
                json.dump(example, f, indent=2)
            ok("memory.json created with defaults")

        # Check writable
        if os.access(MEMORY_FILE, os.W_OK):
            ok("memory.json is writable")
        else:
            return fail(
                "memory.json is not writable",
                "Fix: chmod +w memory.json",
            )
        return True
    except Exception as e:
        return fail(
            f"memory.json issue: {e}",
            "Check file permissions in this directory",
        )


def check_disk_space() -> bool:
    """Quick check for available disk space."""
    try:
        stat = shutil.disk_usage(Path.cwd())
        free_gb = stat.free / (1024 ** 3)
        if free_gb > 1:
            ok(f"Disk space: {free_gb:.1f} GB free")
        else:
            skip(f"Low disk space: {free_gb:.1f} GB free")
        return True
    except Exception:
        skip("Could not check disk space")
        return True


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    print_header()

    print(f" {BOLD}System Info{RESET}")
    print(f"  {GRAY}OS:{RESET}    {sys.platform}")
    print(f"  {GRAY}CWD:{RESET}   {Path.cwd()}")
    print(f"  {GRAY}PID:{RESET}   {os.getpid()}")
    print()

    checks = [
        ("Python Version", check_python),
        ("Ollama Binary", check_ollama_installed),
        ("Ollama Server", check_ollama_running),
        ("Model Available", check_model_available),
        ("CLI Tools", check_tools),
        ("Terminal", check_terminal),
        ("Memory File", check_memory_file),
        ("Disk Space", check_disk_space),
    ]

    for label, check_fn in checks:
        print(f" {BOLD}{label}{RESET}")
        proceed = check_fn()
        if not proceed:
            print(f"\n  {RED}❌ Aborting — fix the issue above and re-run.{RESET}")
            return 1
        print()

    # ── Summary ─────────────────────────────────────────────────────────────
    total = passed + failed + skipped
    w = min(shutil.get_terminal_size((60, 20)).columns, 66)
    print(f" {CYAN}{'─' * (w - 2)}{RESET}")
    print(f" {BOLD}Results: "
          f"{GREEN}{passed} passed{RESET}, "
          f"{RED}{failed} failed{RESET}, "
          f"{YELLOW}{skipped} skipped{RESET}"
          f"  ({total} total)")
    print()

    if failed == 0:
        print(f" {GREEN}{BOLD}✅ All checks passed! You're ready to run:{RESET}")
        print(f" {CYAN}    python3 Agent.py{RESET}")
        print()
        return 0
    else:
        print(f" {YELLOW}{BOLD}⚠️  {failed} check(s) failed (you chose to continue).{RESET}")
        print(f" {YELLOW}   Some features may not work correctly.{RESET}")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
