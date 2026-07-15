# Code Agent — Project Improvement Specification

> **Authored:** July 15, 2026
> **Status:** Draft — based on user interview
> **Goal:** Transform this from a personal Ollama wrapper into a polished, open-source, cross-platform AI coding assistant.

---

## 1. Executive Summary

The existing **Code Agent v4** (`Agent.py`) is a functional but rough Ollama-powered CLI assistant. It works on Unix but has major issues: broken directory changing, no Windows support, a monolithic codebase, limited tools, and no test infrastructure. The user wants to open-source it and make it "much more better" — fixing the broken parts, expanding capabilities, and making it usable everywhere.

---

## 2. Project Identity & Renaming

- **Current name:** `Code Agent` (too generic)
- **New name:** TBD — rename to something distinctive and memorable (e.g., "Coder CLI", "OllamaCoder", "CodePilot Lite", or similar)
- **Repo identity:** Rename `Agent.py`, `Check.py`, and supporting files to match the new project name
- **Target audience:** Developers who want a local-first, private, AI coding assistant on any platform

---

## 3. Cross-Platform Support (TOP PRIORITY)

### 3.1 Problem Statement
The current code is Unix-only due to:
- `os.setsid()` — Unix-only process group API (used for process management and timeout)
- `signal.SIGKILL`, `os.killpg()` — Unix signal APIs
- Assumes `bash` shell, `rg` (ripgrep), and Unix paths
- No Windows compatibility whatsoever

### 3.2 Requirements
- **Must work on:** Windows (cmd.exe + PowerShell), Linux, macOS
- **Must work in:** WSL, Git Bash, Termux, native terminals
- **Shell detection:** Auto-detect the terminal/shell environment and adapt
- **Process management:** Replace `os.setsid`/`os.killpg` with a cross-platform process manager (use `subprocess.Popen` with `creationflags` on Windows, `preexec_fn` on Unix)
- **Path handling:** Use `pathlib.Path` everywhere, handle `C:\` vs `/` separators
- **Tool availability:** Graceful fallback when Unix tools (rg, grep) aren't available

### 3.3 Key Changes
1. Create a `platform.py` or `shell_utils.py` module with platform-aware process management
2. Replace all Unix-specific syscalls with conditional code paths
3. Use `shutil.which()` with platform-aware path expansion
4. Add Windows-specific testing in CI

---

## 4. Directory Changing (cd) Fix

### 4.1 Problem Statement
The `cd` command outputs the new directory path but:
- Doesn't actually change the working directory in some cases
- The fuzzy matching is unreliable (matches wrong directories)
- On Windows, path separators and drive letters (`C:`) break matching
- The LLM also tries to `cd` via shell commands, which don't persist
- Status messages (todos, thoughts, etc.) are not shown during directory operations

### 4.2 Requirements
- `cd` must actually change the directory (verified with `os.getcwd()` after)
- Fuzzy matching should be smarter: prioritize exact prefix matches, then substring matches
- Show clear visual feedback: directory listing after change, breadcrumb trail
- Show thoughts/todos/plan when performing multi-step operations
- On Windows: handle `cd C:`, `cd D:\Projects`, `cd ..`, `cd \` correctly
- Handle paths with spaces, Unicode characters, and symlinks

---

## 5. Code Architecture & Structure

### 5.1 Current State
Single monolithic `Agent.py` (~700 lines) containing:
- Configuration constants
- Terminal colors/UI
- Memory persistence
- Ollama client
- All tool implementations
- Agent loop
- CLI argument parsing
- REPL loop

### 5.2 Target Architecture (Modular Multi-File Package)

```
code-agent/
├── pyproject.toml          # Modern Python packaging (PEP 621)
├── setup.cfg / setup.py    # (optional, for backward compat)
├── README.md               # Revamped documentation
├── LICENSE                 # MIT
├── CONTRIBUTING.md         # Contribution guide
├── CHANGELOG.md            # Version changelog
├── .github/
│   └── workflows/
│       ├── test.yml        # CI: run tests on push/PR
│       └── lint.yml        # CI: lint + type check
├── src/
│   └── code_agent/         # Main package (rename to match new project name)
│       ├── __init__.py
│       ├── __main__.py     # `python -m code_agent` entry point
│       ├── agent.py        # Main agent loop (orchestration only)
│       ├── cli.py          # CLI argument parsing, main entry
│       ├── config.py       # Configuration loading (env vars, config file, CLI)
│       ├── memory.py       # Session memory persistence
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py     # Abstract LLM provider interface
│       │   ├── ollama.py   # Ollama implementation
│       │   ├── openai.py   # OpenAI/Anthropic/etc. implementations
│       │   └── registry.py # Provider registry
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py # Tool registry (plugin system)
│       │   ├── base.py     # BaseTool abstract class
│       │   ├── shell.py    # execute_command, execute_file
│       │   ├── filesystem.py  # read_file, write_file, edit_file, search_code
│       │   ├── files.py    # Copy, move, rename, diff, merge
│       │   ├── git.py      # Git operations (commit, diff, log, branch, status)
│       │   ├── pkg_manager.py # Package management (pip, npm, etc.)
│       │   ├── interactive.py # Interactive shell/subprocess management
│       │   └── web.py      # Web search and URL reading
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── colors.py   # ANSI color definitions and themes
│       │   ├── display.py  # Bordered boxes, thinking blocks, summaries
│       │   ├── spinner.py  # Loading spinner/animation
│       │   └── prompt.py   # Input prompt builder
│       └── platform.py     # Cross-platform utilities (process, paths, shell)
├── tests/
│   ├── __init__.py
│   ├── conftest.py         # Shared fixtures and mocks
│   ├── test_agent.py       # Agent loop tests
│   ├── test_cli.py         # CLI parsing tests
│   ├── test_memory.py      # Memory persistence tests
│   ├── test_platform.py    # Cross-platform tests
│   ├── tools/
│   │   ├── test_shell.py
│   │   ├── test_filesystem.py
│   │   ├── test_git.py
│   │   └── ...
│   └── ui/
│       └── test_display.py
└── docs/                   # (optional, future)
    └── ...
```

### 5.3 Plugin/Extensibility System
- `BaseTool` abstract class with `name`, `description`, `args_schema`, and `execute()` method
- `ToolRegistry` that tools self-register via decorator or class inheritance
- Third-party tools can be loaded from `~/.code_agent/tools/` or `pip install`-ed plugins
- LLM providers follow same pattern via `BaseLLMProvider` interface

---

## 6. Enhanced Agent Loop

### 6.1 Current Problems
- LLM thinking/tool calls interleaved poorly — often hidden or confusing
- No display of intermediate planning steps (todos list)
- When things go wrong, hard to tell what the agent is doing
- The system prompt is too verbose for small models

### 6.2 Requirements
- **Thinking display:** Always show what the LLM is thinking/planning in a clear, animated way
- **Todo list:** Show a dynamic checklist of planned steps, marking them as completed
- **Progress indicator:** Show which step is currently executing, with elapsed time
- **Cancellation:** Clean Ctrl+C handling at any point in the loop
- **Recovery suggestions:** When a tool fails, suggest alternative approaches

### 6.3 Prompt Optimization
- Keep system prompts concise for small local models (1.5B–7B)
- Few-shot examples in prompts should be minimal but effective
- Temperature tuning per task type (lower for code generation, slightly higher for planning)
- Multi-LLM support means prompts may need to be provider-specific

---

## 7. Tool Expansion

### 7.1 Core Tools (existing, improve)
| Tool | Improvement |
|------|-------------|
| `execute_command` | Cross-platform, better timeout handling, streaming output |
| `read_file` | Support binary files, line ranges, encoding detection |
| `write_file` | Atomic writes, backup creation, dry-run mode |
| `edit_file` | Multi-replace, regex support, context-aware replacement |
| `search_code` | Cross-platform (replace rg dependency), glob patterns, file type filters |

### 7.2 New Tools (Phase 1)
| Tool | Description |
|------|-------------|
| `copy_file` | Copy files with conflict resolution |
| `move_file` | Move/rename files with safety checks |
| `diff_files` | Show diff between files or working tree |
| `git_status` | Show git status |
| `git_diff` | Show staged/unstaged diffs |
| `git_commit` | Create commits with AI-generated messages |
| `git_log` | Show recent commit history |
| `pkg_install` | Intelligently install packages (detect language, use correct tool) |
| `interactive_shell` | Start/persist/interact with a long-running shell session |

### 7.3 New Tools (Phase 2 — LLM Provider Independence)
| Tool | Description |
|------|-------------|
| `web_search` | Search the web for documentation/solutions |
| `read_url` | Fetch and extract content from a URL |
| `list_directory` | Enhanced directory listing with tree view |
| `find_files` | Advanced file search by name, type, size, date |

---

## 8. Multi-LLM Provider Support

### 8.1 Motivation
- Not everyone runs Ollama locally
- Users may want cloud models for complex tasks and local models for quick ones
- OpenAI, Anthropic, Google Gemini, and local models should all be supported

### 8.2 Design
- `BaseLLMProvider` interface: `chat(messages, temperature) -> (success, text)`
- Built-in providers: `OllamaProvider`, `OpenAIProvider`, `AnthropicProvider`
- Provider auto-detection: check env vars (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.)
- Provider config in `~/.code_agent/config.json` or environment variables
- Warm provider switching via `:provider openai` or `:provider ollama`

### 8.3 Streaming & Display
- Consistent streaming display regardless of provider
- Token counting and cost estimation for cloud providers
- Fallback logic: if one provider fails, try another

---

## 9. Testing & CI/CD

### 9.1 Test Types
| Type | Tools | What to test |
|------|-------|-------------|
| Unit | pytest | Individual functions, classes, tool methods |
| Integration | pytest + fixtures | Agent loop with mocked LLM, tool chain execution |
| Cross-platform | GitHub Actions matrix | Ubuntu, macOS, Windows runners |

### 9.2 Test Coverage Targets
- **Unit tests:** >80% coverage on core logic (memory, platform, tools)
- **Integration tests:** All tool flows with mocked responses
- **E2E tests:** Basic smoke tests (startup, help, cd, exit)

### 9.3 CI/CD Pipeline (GitHub Actions)
- **On push/PR:** Run tests on ubuntu-latest, macos-latest, windows-latest
- **Linting:** ruff (or flake8) + mypy type checking
- **Code quality:** Complexity checks, docstring coverage
- **Release workflow:** Auto-publish to PyPI on tagged commits (future)

### 9.4 Development Tooling
- `ruff` — fast Python linter (replaces flake8)
- `mypy` — type checking (strict mode)
- `pytest` — test runner
- `pre-commit` — hooks for lint + format before commits
- `hatch` or `pdm` or `setuptools` — packaging (decide based on simplicity)

---

## 10. Terminal UI Improvements

### 10.1 Current Issues
- Bordered boxes are hardcoded width, break on narrow terminals
- Output display truncates at 15 lines — loses important info
- Color definitions are duplicated between `Agent.py` and `Check.py`
- No interactive menus or rich interactions
- **No visible thinking/todo display** — user sees a blank screen while the LLM works

### 10.2 Requirements
- **Always show thinking** — an animated area showing the LLM's current plan/reasoning
- **Todo checklist** — show planned steps with checkmarks as they complete
- **Live command output** — stream command output in real-time, not just result
- **Scrollable output** — don't truncate; show scroll indicators or allow pagination
- **Theme support** — light/dark mode, custom color schemes
- **Narrow terminal support** — gracefully degrade to 40-char width
- **Rich interactive elements** — selection menus, confirm dialogs (helpful for manual mode)

### 10.3 Thinking/Progress Display (NEW)
```
┌──────────────────────────────────────┐
│ 🤔 Thinking... [Step 2/5]            │
│                                      │
│ ✅ 1. Find Python files              │
│ 🔄 2. Count lines ← current         │
│ ⏳ 3. Display results                │
│ ⏳ 4. Summary                        │
└──────────────────────────────────────┘
```

---

## 11. Configuration & Persistence

### 11.1 Current State
- `memory.json` stores session history and model selection
- No config file for user preferences
- No way to set default model, theme, tools, etc.

### 11.2 Requirements
- `config.json` (or TOML/YAML) in `~/.code_agent/config`
- Settings: default model, theme, auto/manual mode, tools, providers
- Environment variable overrides: `CODE_AGENT_MODEL`, `CODE_AGENT_PROVIDER`, etc.
- CLI flags override everything
- `memory.json` continues to store session state only

---

## 12. Phased Implementation Plan

### Phase 1: Foundation & Cross-Platform Fixes
1. Rename project and restructure into modular package
2. Replace all Unix-only APIs with cross-platform alternatives
3. Create `platform.py` with process management, path handling, shell detection
4. Fix `cd` command (native cross-platform implementation)
5. Add basic test suite with CI (GitHub Actions on all platforms)
6. Add `pyproject.toml` for pip installability

### Phase 2: Agent Loop & UI Overhaul
1. Implement thinking/todo display system
2. Improve tool call visualization and output streaming
3. Rework the REPL loop for reliability
4. Add theme support and terminal-width adaptation

### Phase 3: Tool Expansion
1. Plugin/tool registration system (`BaseTool`, `ToolRegistry`)
2. New tools: file operations (copy, move, diff), git integration
3. Package management and interactive shell tools

### Phase 4: Multi-LLM & Extensibility
1. `BaseLLMProvider` interface
2. OpenAI and Anthropic providers
3. Provider auto-detection and switching
4. Third-party plugin loading

### Phase 5: Polish & Release
1. Comprehensive documentation (README, CONTRIBUTING, CHANGELOG)
2. Documentation site or expanded docs/
3. PyPI release
4. Community templates (issue templates, PR template)
5. Performance optimization for small models

---

## 13. Open Questions / Future Considerations

- **Naming:** What should the renamed project be called? Suggestions: "Coder CLI", "OllamaCoder", "CodePilot", "DevAgent", "Aider Lite", "ShellMind"
- **Config format:** TOML (modern, readable) vs JSON (consistent with memory.json) vs YAML
- **Package manager:** hatch vs pdm vs poetry vs plain setuptools
- **Min Python version:** Keep 3.8+ or bump to 3.10+ (for `match` statements, better typing)?
- **Async support:** Should the agent loop be async to handle concurrent tool execution and streaming?
- **GUI future:** Should there be a web UI or TUI (textual) version down the line?

---

## 14. Success Criteria

- [ ] The agent launches and works on Windows (cmd.exe + PowerShell), Linux, and macOS
- [ ] `cd` changes directory correctly on all platforms
- [ ] Thinking/todo display shows clearly during execution
- [ ] All existing tests pass on all three OSes in CI
- [ ] New tools (git, file ops, package mgmt, interactive shell) work reliably
- [ ] Multiple LLM providers are supported (Ollama + at least one cloud provider)
- [ ] Plugin system allows third-party tools without modifying core code
- [ ] The project is pip-installable and has a clear contributing guide
- [ ] Code coverage >80% on core modules
