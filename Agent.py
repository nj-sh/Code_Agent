#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
+================================================+
|          * Code Agent v4 - Ollama CLI          |
+================================================+

A lightweight, local-first coding agent powered by Ollama models.
Inspired by Codex CLI & Claude Code - purpose-built for private,
offline AI-assisted development on modest hardware.

Key Features:
  * Plan -> Execute -> Summarize workflow
  * Tool-based execution (think, bash, read, write, edit, search)
  * Structured terminal UI with clear visual hierarchy
  * Optimized prompts for small Ollama models (1.5B-7B)
  * Auto-retry with intelligent error recovery
  * Persistent session memory across restarts

Recommended lightweight models:
  * qwen2.5-coder:3b    - great balance, ~1.9GB VRAM (default)
  * qwen2.5:1.5b        - fast, ~1GB VRAM
  * stable-code:3b       - good balance, ~1.8GB VRAM
  * deepseek-coder:1.3b  - very fast, ~800MB VRAM
  * codegemma:2b         - Google's lightweight coder
  * qwen2.5-coder:7b     - smarter but heavier, ~4GB VRAM
"""

import os
import json
import re
import subprocess
import sys
import time
import threading
import signal
import textwrap
import shutil
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --- Configuration -----------------------------------------------------------

MEMORY_FILE = Path(__file__).parent / "memory.json"
OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "qwen2.5-coder:3b"
COMMAND_TIMEOUT = 120
MAX_HISTORY = 80
HOME = os.path.expanduser("~")
VERSION = "4.0"

# --- Terminal Colors ---------------------------------------------------------


class Color:
    """ANSI color codes for green/black/orange terminal theme."""
    ORANGE = "\033[38;5;214m"  # main accent for borders, headers, dir
    GREEN = "\033[92m"          # success, prompts
    YELLOW = "\033[93m"         # warnings, tips
    RED = "\033[91m"            # errors
    GRAY = "\033[90m"           # secondary info
    BOLD = "\033[1m"
    RESET = "\033[0m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    BLUE = "\033[38;5;214m"    # same orange for tool calls
    MAGENTA = "\033[38;5;205m"
    THINK = "\033[38;5;245m"
    TOKEN = "\033[38;5;214m"    # orange for token count
    LINE = "\033[38;5;236m"

    # Aliases for theme clarity
    CYAN = ORANGE  # CYAN now points to orange for the theme


C = Color  # shorthand

# --- Data Classes ------------------------------------------------------------


@dataclass
class ToolResult:
    """Result from executing a single tool call."""
    success: bool
    output: str
    duration: float
    tool: str
    args: dict = field(default_factory=dict)
    cancelled: bool = False


# --- Memory (Persistent State) -----------------------------------------------


def load_memory() -> dict:
    """Load or create persistent memory file."""
    defaults = {
        "model": DEFAULT_MODEL,
        "system_prompt": "",
        "last_task": "",
        "last_summary": "",
        "history": [],
    }
    try:
        with open(MEMORY_FILE) as f:
            mem = json.load(f)
        for k, v in defaults.items():
            mem.setdefault(k, v)
        return mem
    except (FileNotFoundError, json.JSONDecodeError):
        with open(MEMORY_FILE, "w") as f:
            json.dump(defaults, f, indent=2)
        return dict(defaults)


def save_memory(memory: dict) -> None:
    """Persist memory to disk."""
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


memory = load_memory()

# --- Spinner ----------------------------------------------------------------


class Spinner:
    """Animated dots spinner for LLM wait states."""

    def __init__(self, text: str = "Thinking"):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._text = text

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        frames = ["●○○○", "○●○○", "○○●○", "○○○●"]
        i = 0
        while self._running:
            sys.stdout.write(f"\r{C.ORANGE}{frames[i]} {self._text}{C.RESET}")
            sys.stdout.flush()
            i = (i + 1) % len(frames)
            time.sleep(0.15)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()

# --- Ollama Client -----------------------------------------------------------


class OllamaClient:
    """Streaming client for local Ollama API."""

    def __init__(self, url: str = OLLAMA_URL, model: str = DEFAULT_MODEL):
        self.url = url
        self.model = model

    def chat(self, messages: list, temperature: float = 0.1) -> tuple[bool, str]:
        """Send a chat request and return (success, full_response_text).
        Collects silently (no streaming) - caller handles display.
        """
        data = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }).encode()

        req = urllib.request.Request(
            self.url, data=data,
            headers={"Content-Type": "application/json"}
        )

        full = ""
        spinner = Spinner("thinking")
        spinner.start()
        started = False

        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=180) as resp:
                    for line in resp:
                        try:
                            chunk = json.loads(line.decode())
                            content = chunk.get("message", {}).get("content", "")
                        except (json.JSONDecodeError, KeyError):
                            continue
                        if not content:
                            continue
                        if not started:
                            started = True
                            spinner.stop()
                        full += content
                return True, full

            except KeyboardInterrupt:
                spinner.stop()
                print(f"\n  {C.YELLOW}X Cancelled{C.RESET}")
                return False, full
            except urllib.error.HTTPError as http_err:
                spinner.stop()
                body = http_err.read().decode()
                try:
                    err_body = json.loads(body)
                    err_msg = err_body.get("error", "")
                    if err_msg.endswith("not found"):
                        print(f"\n  {C.RED}x Model '{self.model}' not found{C.RESET}")
                        print(f"  {C.YELLOW}  -> Pull it: ollama pull {self.model}{C.RESET}")
                        print(f"  {C.YELLOW}  -> Or switch: :model <name>{C.RESET}")
                        print(f"  {C.YELLOW}  -> List models: ollama list{C.RESET}")
                        print(f"  {C.YELLOW}  -> Run diagnostics: python3 Check.py{C.RESET}")
                        return False, ""
                except json.JSONDecodeError:
                    pass
                print(f"\n  {C.RED}x Ollama HTTP {http_err.code} ({err_msg or http_err.reason}){C.RESET}")
                return False, ""
            except Exception as exc:
                if attempt < 2:
                    spinner.stop()
                    time.sleep(1)
                else:
                    spinner.stop()
                    print(f"\n  {C.RED}x Ollama unreachable ({exc}){C.RESET}")
                    print(f"  {C.YELLOW}  -> Is Ollama running? Try: ollama serve{C.RESET}")
                    print(f"  {C.YELLOW}  -> Run diagnostics: python3 Check.py{C.RESET}")
                    return False, ""

        spinner.stop()
        return started, full

# --- System Prompt -----------------------------------------------------------

SYSTEM_PROMPT = """You are Code Agent - an autonomous terminal coding assistant powered by Ollama.

## CRITICAL: You MUST use tools to do work. NEVER just say you did something without calling the tool.

Example BAD response (do NOT do this):
I will list the files in this directory.
<summary>Done - listed files</summary>

Example GOOD response:
<tool_call>{"name": "think", "args": {"thought": "I need to list files using execute_command with ls -la"}}</tool_call>
<tool_call>{"name": "execute_command", "args": {"command": "ls -la"}}</tool_call>

## Workflow (MANDATORY)
1. **think** - Call the think tool to plan your approach and make a TODO list
2. **Execute ONE tool at a time** - Wait for the result before proceeding to next step
3. **Summarize** - Only when ALL steps are done, output <summary>...</summary>

## Available Tools

Output tool calls as JSON inside `<tool_call>` tags:

<tool_call>
{"name": "tool_name", "args": { ... }}
</tool_call>

### `think`
Plan your approach. ALWAYS start with this.
- Args: `thought` (str) - your reasoning and TODO list

### `execute_command`
Run any bash command. Returns stdout/stderr + exit code.
- Args: `command` (str)
- Note: `cd` is handled internally - directory changes persist.

### `execute_file`
Execute a script file as a bash command.
- Args: `path` (str) - path to the script file

### `read_file`
Read a file's contents.
- Args: `path` (str)

### `write_file`
Create or overwrite a file.
- Args: `path` (str), `content` (str)

### `edit_file`
Make a targeted string replacement in a file.
- Args: `path` (str), `old_string` (str), `new_string` (str)

### `search_code`
Search for a pattern in files (uses rg or grep).
- Args: `pattern` (str), `path` (str, default: ".")

## STRICT RULES
1. **START every task with a `think` call** to plan. Include a numbered TODO list.
2. **Execute ONE tool at a time.** Wait for results before proceeding.
3. **NEVER jump straight to <summary>** without using tools first.
4. On failure, try a different approach (up to 3 attempts per step).
5. NEVER ask for credentials or personal info.
6. When ALL steps are done, output:

<summary>
[v] **Task Complete**
- What was accomplished
- Key results
</summary>

7. Be concise. Let your actions speak for themselves."""

# --- Agent Core --------------------------------------------------------------


class CodeAgent:
    """Main agent class - manages LLM conversation, tool execution, and UI."""

    TOOL_CALL_RE = re.compile(
        r'<tool_call>\s*(\{.*?\})\s*</tool_call>', re.DOTALL
    )
    SUMMARY_RE = re.compile(
        r'<summary>(.*?)</summary>', re.DOTALL
    )

    def __init__(self):
        self.cwd = os.getcwd()
        self.model = memory.get("model", DEFAULT_MODEL)
        self.client = OllamaClient(OLLAMA_URL, self.model)
        self.history: list[dict] = []
        self.results_log: list[ToolResult] = []
        self.running_proc: Optional[subprocess.Popen] = None
        self.width = shutil.get_terminal_size((80, 24)).columns
        self.mode = "auto"  # auto or manual
        self._init_history()

    # -- History Management -------------------------------------------------

    def _init_history(self) -> None:
        """Build the conversation history from saved state."""
        sys_prompt = memory.get("system_prompt", "") or SYSTEM_PROMPT
        cwd_info = f"\nCurrent directory: {self.cwd}\nOS: {sys.platform}"
        self.history = [
            {"role": "system", "content": sys_prompt + cwd_info}
        ]
        saved = memory.get("history", [])
        for msg in saved[-MAX_HISTORY:]:
            if msg.get("role") in ("user", "assistant"):
                self.history.append(msg)

    def _update_cwd_in_prompt(self) -> None:
        """Refresh the current directory in the system prompt."""
        self.history[0]["content"] = re.sub(
            r"Current directory: .*",
            f"Current directory: {self.cwd}",
            self.history[0]["content"],
        )

    def _trim_history(self) -> None:
        """Keep history within limit, preserving system prompt."""
        if len(self.history) > MAX_HISTORY:
            self.history = [self.history[0]] + self.history[-(MAX_HISTORY - 1):]

    def _persist(self) -> None:
        """Save current state to memory."""
        memory["history"] = [
            m for m in self.history[1:]
            if m["role"] in ("user", "assistant")
        ][-MAX_HISTORY:]
        memory["model"] = self.model
        save_memory(memory)

    def estimate_tokens(self) -> int:
        """Rough token estimate from word count."""
        return int(
            sum(len(m.get("content", "").split()) for m in self.history)
            / 0.75
        )

    # -- Terminal UI --------------------------------------------------------

    def print_header(self) -> None:
        """Render the startup banner."""
        w = min(self.width, 64)
        print(f"\n{C.BOLD}{C.CYAN}+{'=' * (w - 2)}+{C.RESET}")
        title = "* Code Agent v4"
        pad = (w - 2 - len(title)) // 2
        print(f"{C.BOLD}{C.CYAN}|{' ' * pad}{title}{' ' * (w - 2 - len(title) - pad)}|{C.RESET}")
        print(f"{C.BOLD}{C.CYAN}+{'=' * (w - 2)}+{C.RESET}")
        print(f"  {C.GRAY}Model:  {C.YELLOW}{self.model}{C.RESET}")
        print(f"  {C.GRAY}CWD:    {C.CYAN}{self.cwd.replace(HOME, '~')}{C.RESET}")
        print(f"  {C.GRAY}Memory: {C.DIM}{MEMORY_FILE.name}{C.RESET}")
        if memory.get("last_summary"):
            last = memory["last_summary"].split("\n")[0][:60]
            print(f"  {C.GRAY}Last:   {C.DIM}{last}{C.RESET}")
        print(f"  {C.YELLOW}[i] Tip:{C.RESET} {C.DIM}Run '{C.RESET}{C.CYAN}python3 Check.py{C.RESET}{C.DIM}' to diagnose issues{C.RESET}")
        print(f"  {C.LINE}{'-' * w}{C.RESET}")

    def prompt_str(self) -> str:
        """Build the input prompt with directory, mode, and token count."""
        p = self.cwd.replace(HOME, "~")
        t = self.estimate_tokens()
        mode_tag = f"{C.GREEN}A{C.RESET}" if self.mode == "auto" else f"{C.YELLOW}M{C.RESET}"
        return f"{C.CYAN}{p}{C.RESET} {mode_tag} {C.TOKEN}[{t}t]{C.RESET} {C.GREEN}>{C.RESET} "

    def show_thinking(self, thought: str) -> None:
        """Display a thinking block with reasoning."""
        w = min(self.width, 64)
        print(f"\n{C.THINK}+- {'Thinking':<{w - 6}} -+{C.RESET}")
        for line in thought.strip().split("\n"):
            for wl in textwrap.wrap(line, width=w - 6):
                print(f"{C.THINK}| {wl:<{w - 4}} |{C.RESET}")
        print(f"{C.THINK}+{'-' * (w - 2)}+{C.RESET}")

    def show_tool_call(self, name: str, args: dict) -> None:
        """Display a tool invocation."""
        parts = []
        short_args = dict(args)
        for k, v in short_args.items():
            if isinstance(v, str) and len(v) > 60:
                parts.append(f"{k}={v[:57]}...")
            else:
                parts.append(f"{k}={v}")
        desc = ", ".join(parts[:2])
        if len(parts) > 2:
            desc += " ..."
        print(f"\n  {C.BLUE}[tool] {C.BOLD}{name}{C.RESET} {C.GRAY}({desc}){C.RESET}")

    def show_tool_result(self, result: ToolResult) -> None:
        """Display tool execution result with a bordered output box."""
        if result.cancelled:
            status = f"{C.YELLOW}X Cancelled{C.RESET}"
        elif result.success:
            status = f"{C.GREEN}v Done{C.RESET}"
        else:
            status = f"{C.RED}x Failed{C.RESET}"
        print(f"  {status} {C.GRAY}({result.duration:.2f}s){C.RESET}")

        output = result.output.strip()
        if not output:
            if not result.success and not result.cancelled:
                print(f"    {C.DIM}(no output){C.RESET}")
            return

        # Show output in a bordered box
        w = min(self.width - 4, 70)
        lines = output.split("\n")
        max_lines = 15
        display = lines[:max_lines]
        print(f"  {C.LINE}+{'-' * (w - 2)}+{C.RESET}")
        for line in display:
            if len(line) > w - 4:
                line = line[:w - 7] + "..."
            print(f"  {C.LINE}|{C.RESET} {line:<{w - 4}} {C.LINE}|{C.RESET}")
        if len(lines) > max_lines:
            print(f"  {C.LINE}|{C.RESET} {C.GRAY}... and {len(lines) - max_lines} more lines{C.RESET}  {C.LINE}|{C.RESET}")
        print(f"  {C.LINE}+{'-' * (w - 2)}+{C.RESET}")

    def show_summary(self, text: str) -> None:
        """Display the final task summary in a bordered box."""
        w = min(self.width, 64)
        print(f"\n{C.GREEN}+{'-' * (w - 2)}+{C.RESET}")
        for line in text.strip().split("\n"):
            for wl in textwrap.wrap(line, width=w - 4):
                print(f"{C.GREEN}| {wl:<{w - 4}} |{C.RESET}")
        print(f"{C.GREEN}+{'-' * (w - 2)}+{C.RESET}")

    def show_error(self, msg: str) -> None:
        """Display an error message."""
        print(f"  {C.RED}x {msg}{C.RESET}")

    def show_info(self, msg: str) -> None:
        """Display an info message."""
        print(f"  {C.GRAY}{msg}{C.RESET}")

    # -- Tool Implementations -----------------------------------------------

    def tool_execute_command(self, command: str) -> ToolResult:
        """Run a bash command, capture output, handle cd specially."""
        t0 = time.time()
        cancelled = False
        ec = -1
        out = ""

        # Detect cd and handle it natively so it persists
        cd_match = re.match(r'^cd\s+(.+)$', command.strip())
        if cd_match:
            return self._handle_cd_tool(cd_match.group(1).strip())

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.cwd,
                preexec_fn=os.setsid,
            )
            self.running_proc = proc
            try:
                out, _ = proc.communicate(timeout=COMMAND_TIMEOUT)
                ec = proc.returncode
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                out = "[timeout] Timeout reached"
                ec = -1
        except KeyboardInterrupt:
            if self.running_proc and self.running_proc.poll() is None:
                try:
                    os.killpg(os.getpgid(self.running_proc.pid), signal.SIGKILL)
                except Exception:
                    self.running_proc.kill()
            out = "X Cancelled"
            cancelled = True
            ec = -1
            print()
        finally:
            self.running_proc = None

        return ToolResult(
            success=(ec == 0 and not cancelled),
            output=out.strip(),
            duration=time.time() - t0,
            tool="execute_command",
            args={"command": command},
            cancelled=cancelled,
        )

    def _handle_cd_tool(self, path: str) -> ToolResult:
        """Handle cd natively so directory change persists."""
        t0 = time.time()
        expanded = os.path.expanduser(path)
        test = expanded if os.path.isabs(expanded) else os.path.join(
            self.cwd, expanded
        )
        test = os.path.normpath(test)

        if os.path.isdir(test):
            os.chdir(test)
            self.cwd = os.getcwd()
            self._update_cwd_in_prompt()
            return ToolResult(
                True,
                f"-> {self.cwd.replace(HOME, '~')}",
                time.time() - t0,
                "execute_command",
                {"command": f"cd {path}"},
            )

        # Fuzzy match
        for entry in os.listdir(os.path.dirname(test) or "."):
            fp = os.path.join(os.path.dirname(test) or ".", entry)
            if os.path.isdir(fp) and (
                entry == os.path.basename(test)
                or os.path.basename(test).lower() in entry.lower()
            ):
                os.chdir(fp)
                self.cwd = os.getcwd()
                self._update_cwd_in_prompt()
                return ToolResult(
                    True,
                    f"-> '{entry}'\n> {self.cwd.replace(HOME, '~')}",
                    time.time() - t0,
                    "execute_command",
                    {"command": f"cd {path}"},
                )

        dirs = [
            d for d in os.listdir(self.cwd)
            if os.path.isdir(os.path.join(self.cwd, d))
        ]
        hint = f"\nAvailable: {', '.join(dirs[:10])}" if dirs else ""
        return ToolResult(
            False,
            f"Directory not found: {path}{hint}",
            time.time() - t0,
            "execute_command",
            {"command": f"cd {path}"},
        )

    def tool_execute_file(self, path: str) -> ToolResult:
        """Execute a script file as a bash command."""
        t0 = time.time()
        try:
            full = path if os.path.isabs(path) else os.path.join(self.cwd, path)
            if not os.path.isfile(full):
                return ToolResult(
                    False, f"File not found: {path}",
                    time.time() - t0, "execute_file", {"path": path}
                )
            # Read the file
            with open(full) as f:
                script = f.read()
            if not script.strip():
                return ToolResult(
                    False, f"File is empty: {path}",
                    time.time() - t0, "execute_file", {"path": path}
                )
            # Run via bash (no execute bit needed)
            proc = subprocess.Popen(
                ["bash", full],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=self.cwd,
                preexec_fn=os.setsid,
            )
            try:
                out, _ = proc.communicate(timeout=COMMAND_TIMEOUT)
                ec = proc.returncode
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                out = "[timeout] Timeout reached"
                ec = -1
            return ToolResult(
                success=(ec == 0),
                output=out.strip(),
                duration=time.time() - t0,
                tool="execute_file",
                args={"path": path},
            )
        except Exception as exc:
            return ToolResult(
                False, str(exc),
                time.time() - t0, "execute_file", {"path": path}
            )

    def tool_read_file(self, path: str) -> ToolResult:
        """Read a file from disk."""
        t0 = time.time()
        try:
            full = path if os.path.isabs(path) else os.path.join(self.cwd, path)
            with open(full) as f:
                content = f.read()
            return ToolResult(True, content, time.time() - t0, "read_file",
                              {"path": path})
        except Exception as exc:
            return ToolResult(False, str(exc), time.time() - t0, "read_file",
                              {"path": path})

    def tool_write_file(self, path: str, content: str) -> ToolResult:
        """Create or overwrite a file."""
        t0 = time.time()
        try:
            full = path if os.path.isabs(path) else os.path.join(self.cwd, path)
            os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
            with open(full, "w") as f:
                f.write(content)
            return ToolResult(True, f"Written {len(content)} bytes",
                              time.time() - t0, "write_file",
                              {"path": path})
        except Exception as exc:
            return ToolResult(False, str(exc), time.time() - t0, "write_file",
                              {"path": path})

    def tool_edit_file(self, path: str, old_string: str,
                       new_string: str) -> ToolResult:
        """Make a targeted string replacement in a file."""
        t0 = time.time()
        try:
            full = path if os.path.isabs(path) else os.path.join(self.cwd, path)
            with open(full) as f:
                content = f.read()
            if old_string not in content:
                return ToolResult(False, f"String not found in {path}",
                                  time.time() - t0, "edit_file",
                                  {"path": path})
            new_content = content.replace(old_string, new_string, 1)
            with open(full, "w") as f:
                f.write(new_content)
            return ToolResult(True, "Replaced 1 occurrence",
                              time.time() - t0, "edit_file",
                              {"path": path})
        except Exception as exc:
            return ToolResult(False, str(exc), time.time() - t0, "edit_file",
                              {"path": path})

    def tool_search_code(self, pattern: str, path: str = ".") -> ToolResult:
        """Search for a pattern using ripgrep or fallback grep."""
        t0 = time.time()
        search_path = path if os.path.isabs(path) else os.path.join(
            self.cwd, path
        )
        try:
            result = subprocess.run(
                ["rg", "-n", pattern, search_path],
                capture_output=True, text=True, timeout=30,
            )
            output = result.stdout or result.stderr or "(no matches)"
            ok = result.returncode in (0, 1)
            return ToolResult(ok, output.strip(), time.time() - t0,
                              "search_code", {"pattern": pattern, "path": path})
        except FileNotFoundError:
            try:
                result = subprocess.run(
                    ["grep", "-rn", pattern, search_path],
                    capture_output=True, text=True, timeout=30,
                )
                output = result.stdout or result.stderr or "(no matches)"
                ok = result.returncode in (0, 1)
                return ToolResult(ok, output.strip(), time.time() - t0,
                                  "search_code",
                                  {"pattern": pattern, "path": path})
            except Exception as exc:
                return ToolResult(False, str(exc), time.time() - t0,
                                  "search_code",
                                  {"pattern": pattern, "path": path})
        except Exception as exc:
            return ToolResult(False, str(exc), time.time() - t0,
                              "search_code",
                              {"pattern": pattern, "path": path})

    # -- Tool Dispatch ------------------------------------------------------

    def dispatch_tool(self, name: str, args: dict) -> ToolResult:
        """Route a tool call to the correct handler."""
        dispatch = {
            "execute_command": ("command",),
            "execute_file": ("path",),
            "read_file": ("path",),
            "write_file": ("path", "content"),
            "edit_file": ("path", "old_string", "new_string"),
            "search_code": ("pattern", "path"),
        }

        required = dispatch.get(name)
        if required is None:
            return ToolResult(False, f"Unknown tool: {name}", 0, name, args)

        # Build handler args
        handler_args = []
        for key in required:
            val = args.get(key)
            if val is None:
                return ToolResult(
                    False, f"Missing required arg '{key}' for {name}",
                    0, name, args,
                )
            handler_args.append(val)

        handler = getattr(self, f"tool_{name}", None)
        if not handler:
            return ToolResult(
                False, f"No handler for tool: {name}", 0, name, args,
            )

        return handler(*handler_args)

    # -- Tool Call Extraction -----------------------------------------------

    def extract_tool_calls(self, text: str) -> list[dict]:
        """Extract all tool call JSON objects from AI response."""
        calls = []
        for match in self.TOOL_CALL_RE.finditer(text):
            try:
                obj = json.loads(match.group(1))
                if isinstance(obj, dict) and "name" in obj:
                    calls.append(obj)
            except json.JSONDecodeError:
                continue
        return calls

    def extract_summary(self, text: str) -> Optional[str]:
        """Extract final summary block from AI response."""
        match = self.SUMMARY_RE.search(text)
        return match.group(1).strip() if match else None

    def strip_tool_tags(self, text: str) -> str:
        """Remove tool call and summary tags, leaving readable text."""
        text = self.TOOL_CALL_RE.sub("", text)
        text = self.SUMMARY_RE.sub("", text)
        return text.strip()

    # -- Main Execution Loop ------------------------------------------------

    def print_clean_response(self, text: str) -> None:
        """Print LLM response text with control tags stripped."""
        clean = self.strip_tool_tags(text)
        if clean:
            print(f"\n{clean}")

    def execute_task(self, user_input: str) -> Optional[str]:
        """
        Execute a user task through the agentic loop:
        Send input -> LLM responds -> execute tools -> feed back -> summary
        """
        self.history.append({"role": "user", "content": user_input})

        ok, response = self.client.chat(self.history)
        if not ok:
            return None

        self.history.append({"role": "assistant", "content": response})
        self._trim_history()

        # Check for summary first
        summary = self.extract_summary(response)
        if summary:
            return summary

        # Check for tool calls
        tool_calls = self.extract_tool_calls(response)
        if not tool_calls:
            # Plain text response - print it clean
            self.print_clean_response(response)
            return None

        # Has tool calls - print clean text before first tool call
        clean = self.strip_tool_tags(response)
        if clean:
            # Only show text that came before the first tool call
            first_call = response.find('<tool_call>')
            if first_call >= 0:
                before_tools = response[:first_call].strip()
                if before_tools:
                    before_clean = self.strip_tool_tags(before_tools)
                    if before_clean:
                        print(f"\n{before_clean}")

        return self._process_response(response)  # None or summary string

    def _process_response(self, response: str) -> Optional[str]:
        """
        Process tool calls from an LLM response recursively.
        Returns a summary string or None.
        """
        tool_calls = self.extract_tool_calls(response)
        if not tool_calls:
            return None

        # Execute each tool call sequentially
        for tc in tool_calls:
            name = tc.get("name", "")
            args = tc.get("args", {})

            if name == "think":
                self.show_thinking(args.get("thought", ""))
                continue

            # Show tool call details first
            self.show_tool_call(name, args)

            # Manual mode: ask for confirmation
            if self.mode == "manual":
                try:
                    confirm = input(f"  {C.YELLOW}Run this? [Y/n]: {C.RESET}").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    confirm = "n"
                if confirm not in ("", "y", "yes"):
                    print(f"  {C.YELLOW}X Skipped{C.RESET}")
                    self.history.append({"role": "user", "content": f"User skipped tool: {name}"})
                    ok, next_resp = self.client.chat(self.history)
                    if ok:
                        self.history.append({"role": "assistant", "content": next_resp})
                        self._trim_history()
                        sub_result = self._process_response(next_resp)
                        if sub_result is not None:
                            return sub_result
                    continue

            result = self.dispatch_tool(name, args)
            self.show_tool_result(result)
            self.results_log.append(result)

            if result.cancelled:
                return None

            # Feed result back to LLM
            if result.success:
                msg = f"Result of {name}:\n{result.output[:1200]}"
            else:
                msg = f"Error in {name}:\n{result.output[:600]}"

            self.history.append({"role": "user", "content": msg})

            # Get next LLM response
            ok, next_resp = self.client.chat(self.history)
            if not ok:
                return None

            self.history.append({"role": "assistant", "content": next_resp})
            self._trim_history()

            # Recursively process this response
            sub_result = self._process_response(next_resp)
            if sub_result is not None:
                return sub_result  # summary found higher up

        # All tool calls processed, no summary found
        return None

    # -- Direct Commands ---------------------------------------------------

    def handle_direct(self, inp: str) -> bool:
        """Handle commands that don't need the LLM. Returns True if handled."""
        lower = inp.lower().strip()

        if lower in ("help", ":h", ":help", "/h", "/help"):
            self._show_help()
            return True
        if lower in ("clear", ":c", ":clear", "/c", "/clear"):
            os.system("clear" if os.name != "nt" else "cls")
            return True

        # Exit (only via /exit or :exit, not plain "exit")
        if lower in ("/exit", ":exit"):
            self._persist()
            print(f"\n  {C.GREEN}Bye! Session saved.{C.RESET}")
            sys.exit(0)

        # Model switching (both :model and /model)
        model_match = re.match(r'^[:/]model\s+(.+)$', inp)
        if model_match:
            new_model = model_match.group(1).strip()
            self.model = new_model
            self.client.model = new_model
            memory["model"] = new_model
            self._persist()
            print(f"  {C.GREEN}+ Switched to {C.YELLOW}{new_model}{C.RESET}")
            return True

        # Mode switching
        if lower in (":auto", "/auto"):
            self.mode = "auto"
            print(f"  {C.GREEN}+ Mode: Auto{C.RESET} {C.GRAY}(auto-execute tools){C.RESET}")
            return True
        if lower in (":manual", "/manual"):
            self.mode = "manual"
            print(f"  {C.YELLOW}+ Mode: Manual{C.RESET} {C.GRAY}(confirm each tool){C.RESET}")
            return True

        # Cd is handled as a direct command for speed
        cd_match = re.match(r'^cd\s+(.+)$', inp)
        if cd_match:
            result = self._handle_cd_tool(cd_match.group(1).strip())
            self.show_tool_result(result)
            return True

        # Handle natural language directory change requests (case-insensitive, preserve path case)
        go_match = re.match(
            r'^(?:go|change|navigate|move|switch)\s+(?:to|into|in)\s+(.+)$',
            inp, re.IGNORECASE
        )
        if go_match:
            result = self._handle_cd_tool(go_match.group(1).strip())
            self.show_tool_result(result)
            return True

        return False

    def _show_help(self) -> None:
        """Display the help menu."""
        w = min(self.width, 56)
        print(f"\n{C.CYAN}+{'=' * (w - 2)}+{C.RESET}")
        print(f"{C.CYAN}|{'  * Code Agent Commands':<{w - 2}}|{C.RESET}")
        print(f"{C.CYAN}+{'=' * (w - 2)}+{C.RESET}")
        print(f"  {C.GREEN}<describe your task>{C.RESET}")
        print(f"    Tell me what you want done - I'll plan and execute")
        print(f"\n  {C.GREEN}cd <path>{C.RESET}")
        print(f"    Change directory (with fuzzy matching)")
        print(f"  {C.GREEN}go to <path>{C.RESET}")
        print(f"    Natural language directory change")
        print(f"\n  {C.GREEN}:model or /model <name>{C.RESET}")
        print(f"    Switch Ollama model")
        print(f"  {C.GREEN}:auto or /auto{C.RESET}")
        print(f"    Auto mode - execute tools without asking")
        print(f"  {C.GREEN}:manual or /manual{C.RESET}")
        print(f"    Manual mode - confirm each tool before running")
        print(f"\n  {C.GREEN}:help or /help{C.RESET}   Show this help")
        print(f"  {C.GREEN}:clear or /clear{C.RESET}  Clear screen")
        print(f"  {C.GREEN}:exit or /exit{C.RESET}   Save and quit")
        print(f"\n  {C.GRAY}Tips:{C.RESET}")
        print(f"  {C.GRAY}* Be specific about what you want{C.RESET}")
        print(f"  {C.GRAY}* Use :manual to review each step{C.RESET}")
        print(f"  {C.GRAY}* I'll summarize results when done{C.RESET}")
        print()

    # -- Main Run Loop -----------------------------------------------------

    def run(self) -> None:
        """Main REPL loop."""
        os.system("clear" if os.name != "nt" else "cls")
        self.print_header()

        while True:
            try:
                inp = input(self.prompt_str()).strip()
            except (KeyboardInterrupt, EOFError):
                print()
                continue

            if not inp:
                continue

            # Hint for plain "exit" - must use /exit
            if inp.lower() in ("exit", ":q", "quit"):
                print(f"  {C.YELLOW}Use /exit or :exit to quit{C.RESET}")
                continue

            # Handle direct commands (including /exit)
            if self.handle_direct(inp):
                continue

            # Reset results log for new task
            self.results_log = []
            self.show_info("Processing...")

            # Execute the task through the agentic loop
            summary = self.execute_task(inp)

            print()  # spacer before result

            # Show summary if provided
            if summary:
                self.show_summary(summary)
                memory["last_task"] = inp[:100]
                memory["last_summary"] = summary
            elif self.results_log:
                # Auto-generate summary from results
                successes = sum(1 for r in self.results_log if r.success)
                failures = sum(1 for r in self.results_log if not r.success)
                total_commands = sum(
                    1 for r in self.results_log if r.tool == "execute_command"
                )
                status = f"{C.GREEN}+ {successes} steps succeeded{C.RESET}"
                if failures:
                    status += f", {C.RED}{failures} failed{C.RESET}"
                print(f"  {C.GRAY}--- complete ---{C.RESET}")
                print(f"  {status}")
                if total_commands:
                    print(f"  {C.GRAY}{total_commands} commands{C.RESET}")

            # Persist state
            self._persist()


if __name__ == "__main__":
    CodeAgent().run()
