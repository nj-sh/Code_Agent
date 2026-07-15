"""
Main ShellMind agent class.

Orchestrates the agentic loop: user input -> LLM plans -> execute tools via
ToolRegistry -> show results with progress tracking -> summarize.
Also handles direct commands (cd, :help, :model, :theme).
"""

import json
import os
import re
import sys
import time
from typing import Optional

from shellmind import __version__
from shellmind.config import (
    DEFAULT_MODEL,
    COMMAND_TIMEOUT,
    LLM_TEMPERATURE,
    get_terminal_width,
    HOME,
)
from shellmind.config_parser import load_config, save_config, get_config_value
from shellmind.memory import Memory
from shellmind.ui.theme import get_active, set_active, available_themes
from shellmind.ui.display import Display
from shellmind.ui.prompt import Prompt
from shellmind.llm.model_registry import ProviderRegistry
from shellmind.tools.base import ToolResult
from shellmind.tools.registry import ToolRegistry
from shellmind.tools.shell import ShellTools
from shellmind.tools.filesystem import FileSystemTools
from shellmind.tools.git import GitTools
from shellmind.tools.fileops import FileOpsTools
from shellmind.tools.pkg_manager import PkgTools
from shellmind.tools.interactive import InteractiveTools
from shellmind.tools.undo import UndoTools
from shellmind.platform import run_command


# Token limit estimate — most models support at least 8K context
MAX_CONTEXT_TOKENS = 7000  # Leave headroom below actual model limit


class CodeAgent:
    """Main agent class - manages LLM conversation, tool execution, and UI."""

    TOOL_CALL_RE = re.compile(
        r'<tool_call>\s*(\{.*?\})\s*</tool_call>', re.DOTALL
    )
    SUMMARY_RE = re.compile(
        r'<summary>(.*?)</summary>', re.DOTALL
    )
    # Match bullet-list plans like "- step 1\n- step 2" inside think blocks
    PLAN_ITEM_RE = re.compile(r'^[\-\*\d+\.\s]\s*(.+)$', re.MULTILINE)

    def __init__(
        self,
        model: Optional[str] = None,
        mode: str = "auto",
        clear_screen: bool = True,
        memory: Optional[Memory] = None,
    ):
        self.cwd = os.getcwd()
        self.memory = memory or Memory()

        # Load config from file (user preferences)
        self.config = load_config()
        config_model = self.config.get("model", DEFAULT_MODEL)
        self.model = model or self.memory.model or config_model

        self.providers = ProviderRegistry()
        if self.model:
            self.providers.active_model = self.model

        self.display = Display()
        self.tools = ToolRegistry()
        self._setup_tools()

        self.history: list[dict] = []
        self.results_log: list[ToolResult] = []
        self.last_input: str = ""
        self.mode = mode or self.config.get("mode", "auto")
        self.clear_screen = clear_screen
        self.cancelled = False
        self._init_history()

        # Apply config theme
        config_theme = self.config.get("theme", "dark")
        if config_theme in available_themes():
            set_active(config_theme)

    def _setup_tools(self) -> None:
        """Register all available tools in the registry."""
        for tool_set in [
            ShellTools(self.display.stream_line).get_all(),
            FileSystemTools().get_all(),
            GitTools().get_all(),
            FileOpsTools().get_all(),
            PkgTools().get_all(),
            InteractiveTools().get_all(),
            UndoTools().get_all(),
        ]:
            for tool in tool_set:
                self.tools.register(tool)

    # ─── System Prompt ────────────────────────────────────────────────

    @property
    def _system_prompt(self) -> str:
        """Build the system prompt with current context."""
        return (
            "You are ShellMind - a cross-platform terminal coding assistant.\n"
            "\n"
            "## CRITICAL: Use tools to do work. NEVER just say you did something.\n"
            "\n"
            "## OUTPUT RULE: Show content BEFORE summarizing.\n"
            "\n"
            "## Workflow\n"
            "1. **think** - Plan your approach, outlining specific steps\n"
            "2. **Execute ONE tool** - Call the tool, wait for result\n"
            "3. **SHOW the result** - Write the data clearly to the user\n"
            "4. **Repeat** - Continue with next tool if needed\n"
            "5. **Summarize** - Only output <summary> AFTER showing data\n"
            "\n"
            "## Tool format: Output tool calls as JSON inside <tool_call> tags:\n"
            "<tool_call>\n"
            '{"name": "tool_name", "args": { ... }}\n'
            "</tool_call>\n"
            "\n"
            "## Available Tools\n"
            "- **think**: Plan your approach. Args: `thought`\n"
            "- **execute_command**: Run a shell command. Args: `command`\n"
            "- **execute_file**: Run a script file. Args: `path`\n"
            "- **read_file**: Read a file. Args: `path`\n"
            "- **write_file**: Create/overwrite file. Args: `path`, `content`\n"
            "- **edit_file**: Replace text in a file. Args: `path`, `old_string`, `new_string`\n"
            "- **search_code**: Search files for a pattern. Args: `pattern`, `path`\n"
            "- **git_status**: Show git working tree status\n"
            "- **git_log**: Show git commit history. Args: `count`\n"
            "- **git_diff**: Show git diff. Args: `staged`, `path`\n"
            "- **git_commit**: Create a git commit. Args: `message`, `add_all`\n"
            "- **git_branch**: List/create/delete branches. Args: `create`, `delete`\n"
            "- **copy_file**: Copy a file. Args: `source`, `destination`\n"
            "- **move_file**: Move a file. Args: `source`, `destination`\n"
            "- **diff_files**: Diff two files. Args: `file1`, `file2`\n"
            "- **pkg_install**: Install packages. Args: `packages`, `manager`\n"
            "- **shell_send**: Send command to persistent shell. Args: `command`\n"
            "- **shell_close**: Close persistent shell session\n"
            "\n"
            "## STRICT RULES\n"
            "1. START every task with a `think` call that lists your plan as bullet points\n"
            "2. Execute ONE tool at a time - Wait for results before proceeding\n"
            "3. SHOW the output to the user first - Write data clearly\n"
            "4. Summarize LAST - <summary> must come AFTER showing data\n"
            "5. On failure, try a different approach (up to 3 times)\n"
            "6. NEVER ask for credentials or personal info\n"
            "7. When ALL steps are done, output a summary\n"
            f"8. For directory changes, use: cd with path argument\n"
        )

    def _init_history(self) -> None:
        """Build conversation history from saved state."""
        cwd_info = (
            f"\nCurrent directory: {self.cwd}\n"
            f"OS: {sys.platform}\n"
            f"Model: {self.model}\n"
            f"Theme: {get_active().name}"
        )
        self.history = [
            {"role": "system", "content": self._system_prompt + cwd_info}
        ]
        saved = self.memory.history
        for msg in saved[-80:]:
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
        if len(self.history) > 80:
            self.history = [self.history[0]] + self.history[-(80 - 1):]

    def _persist(self) -> None:
        """Save current state to memory."""
        self.memory.history = [
            m for m in self.history[1:]
            if m["role"] in ("user", "assistant")
        ]
        self.memory.model = self.model
        self.memory.save()

    def estimate_tokens(self) -> int:
        """Rough token estimate from word count."""
        total = sum(
            len(m.get("content", "").split()) for m in self.history
        )
        return int(total / 0.75)

    def _trim_by_tokens(self) -> None:
        """Token-aware history trimming. Removes oldest messages when
        estimated token count exceeds MAX_CONTEXT_TOKENS.
        Keeps the system prompt and the most recent messages."""
        if self.estimate_tokens() <= MAX_CONTEXT_TOKENS:
            return
        # Remove oldest user/assistant pairs until under limit
        while len(self.history) > 3 and self.estimate_tokens() > MAX_CONTEXT_TOKENS:
            # Remove the second-oldest message (index 1, after system prompt)
            self.history.pop(1)
            if len(self.history) > 2:
                self.history.pop(1)  # Remove the corresponding pair

    # ─── Terminal UI ──────────────────────────────────────────────────

    def print_header(self) -> None:
        """Render the startup banner."""
        self.display.header(
            model=self.model,
            cwd=self.cwd,
            memory_name=self.memory.path.name,
            last_summary=self.memory.last_summary,
        )

    def prompt_str(self) -> str:
        """Build the input prompt string."""
        return Prompt.build(
            cwd=self.cwd,
            mode=self.mode,
            tokens=self.estimate_tokens(),
        )

    # ─── Native Commands (not tools) ─────────────────────────────────

    def _handle_cd(self, path: str) -> ToolResult:
        """Handle cd natively so directory changes persist in the agent."""
        from shellmind.tools.shell import CdTool
        tool = CdTool()
        result = tool.execute(path=path)
        if result.success:
            # Update agent's cwd tracking
            self.cwd = os.getcwd()
            self._update_cwd_in_prompt()
        return result

    # ─── Tool Dispatch ────────────────────────────────────────────────

    def dispatch_tool(self, name: str, args: dict) -> ToolResult:
        """Route a tool call through the registry.

        Some tools (like cd) need agent-level state management
        so they are wrapped here.
        """
        if name == "cd":
            return self._handle_cd(args.get("path", ""))

        result = self.tools.dispatch(name, **args)
        if result is not None:
            return result

        return ToolResult(False, f"Unknown tool: {name}", 0, name, args)

    # ─── Tool Call Extraction ─────────────────────────────────────────

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

    def extract_plan_steps(self, thought: str) -> list[str]:
        """Extract bullet-point plan steps from a think block."""
        steps = []
        for line in thought.strip().split("\n"):
            line = line.strip()
            # Match lines starting with -, *, or numbers
            if re.match(r'^[\-\*\d]+[\.\s)]\s+', line):
                step = re.sub(r'^[\-\*\d]+[\.\s)]\s+', '', line).strip()
                if step:
                    steps.append(step)
        return steps

    def strip_tool_tags(self, text: str) -> str:
        """Remove tool call and summary tags, leaving readable text."""
        text = self.TOOL_CALL_RE.sub("", text)
        text = self.SUMMARY_RE.sub("", text)
        return text.strip()

    # ─── Main Execution Loop ──────────────────────────────────────────

    def print_clean_response(self, text: str) -> None:
        """Print LLM response text with control tags stripped."""
        clean = self.strip_tool_tags(text)
        if clean:
            print(f"\n{clean}")

    def execute_task(self, user_input: str) -> Optional[str]:
        """Execute a user task through the agentic loop.

        Send input -> LLM responds -> execute tools -> feed back -> summary.
        Returns summary text or None.
        """
        self.cancelled = False
        self.display.reset_progress()
        self.last_input = user_input

        self.history.append({"role": "user", "content": user_input})

        result = self.providers.chat(self.history, temperature=LLM_TEMPERATURE)
        if not result.success:
            self.display.error(result.content)
            return None

        self.history.append({"role": "assistant", "content": result.content})
        self._trim_history()
        self._trim_by_tokens()

        # Check for summary first
        summary = self.extract_summary(result.content)
        if summary:
            return summary

        # Check for tool calls
        tool_calls = self.extract_tool_calls(result.content)
        if not tool_calls:
            # Plain text response - print clean
            self.print_clean_response(result.content)
            return None

        # Print text before first tool call
        clean = self.strip_tool_tags(result.content)
        first_call = result.content.find('<tool_call>')
        if first_call >= 0:
            before_tools = result.content[:first_call].strip()
            if before_tools:
                before_clean = self.strip_tool_tags(before_tools)
                if before_clean:
                    print(f"\n{before_clean}")

        return self._process_response(result.content)

    def _process_response(self, response: str) -> Optional[str]:
        """Process tool calls from an LLM response recursively."""
        tool_calls = self.extract_tool_calls(response)
        if not tool_calls:
            return None

        step_index = 0

        for tc in tool_calls:
            if self.cancelled:
                return None

            name = tc.get("name", "")
            args = tc.get("args", {})

            if name == "think":
                thought = args.get("thought", "")
                self.display.thinking(thought)
                # Try to extract plan steps for progress tracking
                steps = self.extract_plan_steps(thought)
                if steps:
                    self.display.set_plan(steps)
                    self.display.show_progress()
                continue

            # Show tool call
            self.display.tool_call(name, args)

            # Mark step as active in progress tracker
            if self.display.tracker.is_active:
                self.display.step_start(step_index, f"Running {name}")

            # Manual mode: ask for confirmation
            if self.mode == "manual":
                try:
                    confirm = input(
                        f"  {get_active().warning}Run this? [Y/n]: {get_active().reset}"
                    ).strip().lower()
                except (EOFError, KeyboardInterrupt):
                    confirm = "n"
                if confirm not in ("", "y", "yes"):
                    print(f"  {get_active().warning}X Skipped{get_active().reset}")
                    self.history.append({
                        "role": "user",
                        "content": f"User skipped tool: {name}"
                    })
                    next_result = self.providers.chat(self.history)
                    if next_result.success:
                        self.history.append({"role": "assistant", "content": next_result.content})
                        self._trim_history()
                        sub_result = self._process_response(next_result.content)
                        if sub_result is not None:
                            return sub_result
                    step_index += 1
                    continue

            # Execute the tool
            result = self.dispatch_tool(name, args)

            # Mark step as done
            if self.display.tracker.is_active:
                self.display.step_done(step_index, result.success)

            # Show result
            self.display.tool_result(
                result.success, result.output, result.duration, result.cancelled,
            )
            self.results_log.append(result)

            if result.cancelled:
                self.cancelled = True
                return None

            # Feed result back to LLM
            if result.success:
                msg = f"Result of {name}:\n{result.output[:1200]}"
            else:
                msg = f"Error in {name}:\n{result.output[:600]}"

            self.history.append({"role": "user", "content": msg})

            # Get next LLM response
            next_result = self.providers.chat(self.history)
            if not next_result.success:
                return None

            self.history.append({"role": "assistant", "content": next_result.content})
            self._trim_history()
            self._trim_by_tokens()

            # Recursively process
            sub_result = self._process_response(next_result.content)
            if sub_result is not None:
                return sub_result

            step_index += 1

        return None

    # ─── Direct Commands ──────────────────────────────────────────────

    def handle_direct(self, inp: str) -> bool:
        """Handle commands that don't need the LLM. Returns True if handled."""
        lower = inp.lower().strip()

        # Help
        if lower in ("help", ":h", ":help", "/h", "/help"):
            self._show_help()
            return True

        # Clear
        if lower in ("clear", ":c", ":clear", "/c", "/clear"):
            os.system("clear" if os.name != "nt" else "cls")
            return True

        # Exit
        if lower in ("/exit", ":exit"):
            self._cleanup()
            print(f"\n  {get_active().success}Bye! Session saved.{get_active().reset}")
            sys.exit(0)

        # Retry — re-run the last task
        if lower in (":retry", "/retry", ":r", "/r"):
            if self.last_input:
                print(f"  {get_active().muted}Retrying: {self.last_input[:60]}...{get_active().reset}")
                self._run_and_show(self.last_input)
            else:
                print(f"  {get_active().warning}No last task to retry.{get_active().reset}")
            return True

        # Status — show current state
        if lower in (":status", "/status"):
            self._show_status()
            return True

        # Theme switching
        theme_match = re.match(r'^[:/]theme\s+(.+)$', inp)
        if theme_match:
            theme_name = theme_match.group(1).strip().lower()
            if theme_name in available_themes():
                set_active(theme_name)
                self._update_cwd_in_prompt()
                print(f"  {get_active().success}+ Theme: {theme_name}{get_active().reset}")
            else:
                print(f"  {get_active().warning}Unknown theme. Available: {', '.join(available_themes())}{get_active().reset}")
            return True

        # Provider switching
        provider_match = re.match(r'^[:/]provider\s+(.+)$', inp)
        if provider_match:
            provider_name = provider_match.group(1).strip().lower()
            try:
                self.providers.active_provider = provider_name
                print(f"  {get_active().success}+ Provider: {get_active().warning}{provider_name}{get_active().reset}")
            except ValueError as e:
                print(f"  {get_active().error}{e}{get_active().reset}")
            return True

        # Model switching
        model_match = re.match(r'^[:/]model\s+(.+)$', inp)
        if model_match:
            new_model = model_match.group(1).strip()
            self.model = new_model
            self.providers.active_model = new_model
            self.memory.model = new_model
            self._persist()
            print(f"  {get_active().success}+ Model: {get_active().warning}{new_model}{get_active().reset} ({get_active().muted}{self.providers.active_name}{get_active().reset})")
            return True

        # Mode switching
        if lower in (":auto", "/auto"):
            self.mode = "auto"
            print(f"  {get_active().success}+ Mode: Auto{get_active().reset} {get_active().muted}(auto-execute tools){get_active().reset}")
            return True
        if lower in (":manual", "/manual"):
            self.mode = "manual"
            print(f"  {get_active().warning}+ Mode: Manual{get_active().reset} {get_active().muted}(confirm each tool){get_active().reset}")
            return True

        # Direct cd
        cd_match = re.match(r'^cd\s+(.+)$', inp)
        if cd_match:
            result = self._handle_cd(cd_match.group(1).strip())
            self.display.tool_result(result.success, result.output, result.duration)
            return True

        # Natural language dir change
        go_match = re.match(
            r'^(?:go|change|navigate|move|switch)\s+(?:to|into|in)\s+(.+)$',
            inp, re.IGNORECASE,
        )
        if go_match:
            result = self._handle_cd(go_match.group(1).strip())
            self.display.tool_result(result.success, result.output, result.duration)
            return True

        # Cancel — abort the current running task
        if lower in (":cancel", "/cancel"):
            if self.cancelled:
                print(f"  {get_active().muted}Already cancelled.{get_active().reset}")
            else:
                self.cancelled = True
                print(f"  {get_active().warning}Cancelling current task...{get_active().reset}")
            return True

        # Verbosity modes
        if lower in (":quiet", "/quiet"):
            from shellmind.ui.display import set_verbosity, VERBOSITY_QUIET
            set_verbosity(VERBOSITY_QUIET)
            print(f"  {get_active().muted}Mode: Quiet (minimal output){get_active().reset}")
            return True
        if lower in (":verbose", "/verbose"):
            from shellmind.ui.display import set_verbosity, VERBOSITY_VERBOSE
            set_verbosity(VERBOSITY_VERBOSE)
            print(f"  {get_active().warning}Mode: Verbose (detailed output){get_active().reset}")
            return True
        if lower in (":debug", "/debug"):
            from shellmind.ui.display import set_verbosity, VERBOSITY_DEBUG
            set_verbosity(VERBOSITY_DEBUG)
            print(f"  {get_active().warning}Mode: Debug (streaming output){get_active().reset}")
            return True
        if lower in (":normal", "/normal"):
            from shellmind.ui.display import set_verbosity, VERBOSITY_NORMAL
            set_verbosity(VERBOSITY_NORMAL)
            print(f"  {get_active().success}Mode: Normal{get_active().reset}")
            return True

        # Version
        if lower in ("--version", "-v", ":version", "/version"):
            print(f"  ShellMind v{__version__}")
            return True

        return False

    def _show_help(self) -> None:
        """Display the help menu."""
        theme = get_active()
        w = min(get_terminal_width(), 56)
        print(f"\n{theme.accent}+{'=' * (w - 2)}+{theme.reset}")
        print(f"{theme.accent}|{'  * ShellMind Commands':<{w - 2}}|{theme.reset}")
        print(f"{theme.accent}+{'=' * (w - 2)}+{theme.reset}")
        print(f"  {theme.success}<describe your task>{theme.reset}")
        print(f"    Tell me what you want done")
        print(f"\n  {theme.success}cd <path>{theme.reset}  or  go to <path>")
        print(f"    Change directory (with fuzzy matching)")
        print(f"\n  {theme.success}:model <name>{theme.reset}")
        print(f"    Switch LLM model")
        print(f"  {theme.success}:provider <name>{theme.reset}")
        print(f"    Switch LLM provider ({', '.join(self.providers.list_providers())})")
        print(f"  {theme.success}:theme <name>{theme.reset}")
        print(f"    Switch UI theme ({', '.join(available_themes())})")
        print(f"\n  {theme.success}:auto{theme.reset}  /  {theme.success}:manual{theme.reset}")
        print(f"    Toggle auto/manual tool execution mode")
        print(f"  {theme.success}:retry{theme.reset}  /  {theme.success}:r")
        print(f"    Re-run the last task")
        print(f"  {theme.success}:cancel{theme.reset}")
        print(f"    Cancel the current running task")
        print(f"  {theme.success}:status{theme.reset}")
        print(f"    Show current session state")
        print(f"\n  {theme.success}Output{theme.reset}")
        print(f"  {theme.success}:quiet{theme.reset}    Minimal output (progress only)")
        print(f"  {theme.success}:verbose{theme.reset}  Detailed output")
        print(f"  {theme.success}:debug{theme.reset}    Debug output (with streaming)")
        print(f"  {theme.success}:normal{theme.reset}   Standard output (default)")
        print(f"\n  {theme.success}:help{theme.reset}      Show this help")
        print(f"  {theme.success}:clear{theme.reset}     Clear screen")
        print(f"  {theme.success}:exit{theme.reset}      Save and quit")
        print(f"  {theme.success}:version{theme.reset}   Show version")
        print(f"\n  {theme.muted}Tips:{theme.reset}")
        print(f"  {theme.muted}* Be specific about what you want{theme.reset}")
        print(f"  {theme.muted}* Use :manual to review each step{theme.reset}")
        print(f"  {theme.muted}* Use :theme light for light mode{theme.reset}")
        print(f"  {theme.muted}* Switch provider: :provider ollama or :provider openai{theme.reset}")
        print()

    def _show_status(self) -> None:
        """Show current session status."""
        theme = get_active()
        w = min(get_terminal_width(), 56)
        print(f"\n{theme.accent}── Session Status ──{theme.reset}")
        from shellmind.ui.display import get_verbosity
        verbosity_names = {0: "quiet", 1: "normal", 2: "verbose", 3: "debug"}
        print(f"  {theme.muted}Provider:{theme.reset}{theme.warning} {self.providers.active_name}{theme.reset}")
        print(f"  {theme.muted}Model:{theme.reset}    {theme.warning}{self.model}{theme.reset}")
        print(f"  {theme.muted}Mode:{theme.reset}     {theme.success if self.mode == 'auto' else theme.warning}{self.mode}{theme.reset}")
        print(f"  {theme.muted}Theme:{theme.reset}    {theme.accent}{get_active().name}{theme.reset}")
        print(f"  {theme.muted}Output:{theme.reset}   {theme.token}{verbosity_names.get(get_verbosity(), 'normal')}{theme.reset}")
        print(f"  {theme.muted}CWD:{theme.reset}     {theme.accent}{self.cwd.replace(HOME, '~')}{theme.reset}")
        print(f"  {theme.muted}Memory:{theme.reset}  {theme.dim}{self.memory.path}{theme.reset}")
        tokens = self.estimate_tokens()
        token_pct = int(tokens / MAX_CONTEXT_TOKENS * 100) if MAX_CONTEXT_TOKENS else 0
        print(f"  {theme.muted}Tokens:{theme.reset}  {theme.token}{tokens}{theme.reset} ({token_pct}% of {MAX_CONTEXT_TOKENS})")
        tools_avail = self.tools.list_tools()
        print(f"  {theme.muted}Tools:{theme.reset}   {len(tools_avail)} registered: {', '.join(tools_avail)}")
        if self.last_input:
            print(f"  {theme.muted}Last:{theme.reset}    {theme.dim}{self.last_input[:80]}{theme.reset}")
        print()

    def _run_and_show(self, task: str) -> None:
        """Run a task and show results."""
        self.results_log = []
        self.display.info("Processing...")
        summary = self.execute_task(task)
        print()

        if summary:
            self.display.summary(summary)
            self.memory.last_task = task[:100]
            self.memory.last_summary = summary
        elif self.results_log:
            successes = sum(1 for r in self.results_log if r.success)
            failures = len(self.results_log) - successes
            status = f"{get_active().success}+ {successes} steps succeeded{get_active().reset}"
            if failures:
                status += f", {get_active().error}{failures} failed{get_active().reset}"
            print(f"  {get_active().muted}--- complete ---{get_active().reset}")
            print(f"  {status}")

        self._persist()

    # ─── Cleanup ─────────────────────────────────────────────────────

    def _cleanup(self) -> None:
        """Clean up resources before exit."""
        # Close interactive shell session if active
        close_tool = self.tools.get("shell_close")
        if close_tool:
            try:
                close_tool.execute()
            except Exception:
                pass
        self._persist()

    # ─── Run Modes ───────────────────────────────────────────────────

    def run_once(self, task: str) -> bool:
        """Run one task without opening the interactive prompt."""
        self._run_and_show(task)
        return self.memory.last_summary is not None or bool(self.results_log)

    def run(self) -> None:
        """Main REPL loop."""
        if self.clear_screen:
            os.system("clear" if os.name != "nt" else "cls")
        self.print_header()

        while True:
            try:
                inp = input(self.prompt_str()).strip()
            except KeyboardInterrupt:
                print()
                self.display.info("Use /exit to quit (or press again to force quit)")
                # Don't clean up on first Ctrl+C - user might want to resume
                continue
            except EOFError:
                self._cleanup()
                print(f"\n  {get_active().success}Bye! Session saved.{get_active().reset}")
                return

            if not inp:
                continue

            # Hint for plain exit/quit
            if inp.lower() in ("exit", ":q", "quit"):
                print(f"  {get_active().warning}Use /exit or :exit to quit{get_active().reset}")
                continue

            # Handle direct commands
            if self.handle_direct(inp):
                continue

            # Execute task
            self._run_and_show(inp)
