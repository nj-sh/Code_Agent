# ShellMind — Cross-Platform AI Coding Assistant

> A local-first, cross-platform AI coding assistant for your terminal.
> Works on **Windows, Linux, and macOS** with multiple LLM providers.

[![Version](https://img.shields.io/badge/version-5.0-blue)](https://github.com/shellmind/shellmind)
[![Python](https://img.shields.io/badge/python-3.10%2B-yellow)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://github.com/shellmind/shellmind/actions/workflows/test.yml/badge.svg)](https://github.com/shellmind/shellmind/actions/workflows/test.yml)
[![OS](https://img.shields.io/badge/OS-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)]()
[![PyPI](https://img.shields.io/badge/pypi-v5.0-brightgreen)](https://pypi.org/project/shellmind/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Downloads](https://img.shields.io/badge/dynamic/json?label=downloads&query=%24.total_downloads&url=https%3A%2F%2Fapi.pepy.tech%2Fapi%2Fprojects%2Fshellmind)]()

---

## ✨ Features

| Capability | Description |
|---|---|
| **🧠 Plan → Execute → Summarize** | AI plans steps, executes one by one, and summarizes done |
| **🔧 18 Built-in Tools** | Shell, filesystem, git, file ops, package mgmt, interactive shell |
| **🪟 Cross-Platform** | Windows (cmd/PowerShell), Linux, macOS — same experience |
| **🔄 Multi-LLM** | Ollama, OpenAI, plus any OpenAI-compatible endpoint |
| **🎨 Themed UI** | Dark theme (default) or light theme, switchable at runtime |
| **📋 Progress Tracking** | Live todo checklist during task execution |
| **⚡ Direct Commands** | `cd` (fuzzy), `:model`, `:provider`, `:theme`, `:retry`, `:status` |
| **🔄 Auto-Retry** | Automatic error recovery with alternative approaches |
| **💾 Persistent Memory** | Session history and preferences survive restarts |
| **🧩 Extensible** | Plugin architecture for custom tools and LLM providers |
| **📦 Zero Dependencies** | Pure Python standard library — no pip installs needed |
| **🧪 Tested** | 64+ tests with CI on all platforms |

---

## 🛠️ Requirements

| Dependency | Required | Notes |
|---|---|---|
| **Python 3.10+** | ✅ Yes | Available on all platforms |
| **Ollama** | ❌ Optional | For local models (`ollama serve`) |
| **OpenAI API key** | ❌ Optional | Set `OPENAI_API_KEY` env var |
| **Git** | ❌ Optional | Required for git tools |

---

## 📦 Installation

### Quick start (with pip)

```bash
git clone https://github.com/shellmind/shellmind.git
cd shellmind
pip install -e .
shellmind
```

### From PyPI (once published)

```bash
pip install shellmind
shellmind
```

### Run directly without install

```bash
git clone https://github.com/shellmind/shellmind.git
cd shellmind
python -m shellmind
```

### Setup with Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a lightweight coder model
ollama pull qwen2.5-coder:3b

# Run ShellMind
shellmind
```

---

## 🎮 Usage

### Starting the REPL

```
╔══════════════════════════════════════════════╗
║          * ShellMind v5                      ║
╚══════════════════════════════════════════════╝
  Model:  qwen2.5-coder:3b
  CWD:    ~/projects
  Memory: memory.json
───────────────────────────────────────────────────
~/projects [1.2k] A >
```

### Commands

#### Task prompts (uses AI)

| Input | What happens |
|---|---|
| `list files in this directory` | AI plans and executes `ls` / `dir` |
| `create a python script that greets the user` | AI creates, writes, and tests a file |
| `find all TODO comments` | Searches code with ripgrep/grep/findstr |
| `show git status and recent commits` | Runs git tools |
| `install flask` | Auto-detects pip and installs flask |
| `copy file1.txt to backup/` | Copies with shutil |
| `diff old.py new.py` | Shows file differences |

#### Direct commands (instant, no AI)

| Command | Purpose |
|---|---|
| `cd <path>` or `go to <path>` | Change directory (fuzzy matching) |
| `:model <name>` | Switch LLM model |
| `:provider <name>` | Switch LLM provider (ollama, openai) |
| `:theme <name>` | Switch UI theme (dark, light) |
| `:manual` / `:auto` | Toggle tool confirmation mode |
| `:retry` / `:r` | Re-run the last task |
| `:status` | Show session state |
| `:help` | Show help menu |
| `:clear` | Clear screen |
| `:exit` | Save and quit |

### One-shot mode (scripts/editor integration)

```bash
# Run a single task and exit
shellmind -p "find all TODO comments"
shellmind "list the python files"

# With options
shellmind -C ~/project -p "show git status" --model qwen2.5-coder:7b

# Manual mode (confirm each tool)
shellmind --manual
```

### Example session

```
~/projects [1.2k] A > show git status and recent commits

┌~ Thinking~────────────────────────────────────┐
│ I'll check git status first, then show recent │
│ commits.                                      │
└───────────────────────────────────────────────┘

├──────────────────────────────────────────────┤
│ Progress [1/2]                               │
│   [~] Check git status                       │
│   [ ] Show recent commits                    │
├──────────────────────────────────────────────┤

>> git_status
  ✓ Done (0.05s)
    On branch: main
    M src/shellmind/agent.py
    M README.md

├──────────────────────────────────────────────┤
│ Progress [2/2]                               │
│   [✓] Check git status                       │
│   [~] Show recent commits                    │
├──────────────────────────────────────────────┤

>> git_log (count=5)
  ✓ Done (0.03s)
    a1b2c3d Fix agent loop edge case
    e4f5g6h Add theme support
    i7j8k9l Initial Phase 2 release

┌──────────────────────────────────────────────┐
│ ✅ **Task Complete**                         │
│ • Showed git status with 2 modified files    │
│ • Listed 3 recent commits                    │
└──────────────────────────────────────────────┘
```

---

## 🧠 LLM Providers

ShellMind supports multiple LLM providers. Switch at any time.

| Provider | Command | Setup |
|---|---|---|
| **Ollama** (default) | `:model qwen2.5-coder:3b` | `ollama serve` |
| **OpenAI** | `:provider openai` | Set `OPENAI_API_KEY` |
| **Any OpenAI-compatible** | `:provider openai` + set API URL | Configure in provider |

```bash
# Use local Ollama model
:model deepseek-coder:1.3b

# Switch to OpenAI
:provider openai
:model gpt-4o-mini

# Switch back
:provider ollama
```

---

## 🧩 Available Tools (18 total)

### Shell & Execution
| Tool | Description |
|---|---|
| `execute_command` | Run any shell command |
| `execute_file` | Run a script file |
| `shell_send` | Send command to persistent shell session |
| `shell_close` | Close persistent shell session |

### File System
| Tool | Description |
|---|---|
| `read_file` | Read file contents |
| `write_file` | Create or overwrite a file |
| `edit_file` | Make targeted string replacements |
| `search_code` | Search patterns with rg/grep/findstr |

### File Operations
| Tool | Description |
|---|---|
| `copy_file` | Copy files or directories |
| `move_file` | Move or rename files/directories |
| `diff_files` | Show diff between two files |

### Git Integration
| Tool | Description |
|---|---|
| `git_status` | Show working tree status |
| `git_log` | Show commit history |
| `git_diff` | Show staged/unstaged diffs |
| `git_commit` | Create commits (safe, no shell injection) |
| `git_branch` | List, create, delete branches |

### Package Management
| Tool | Description |
|---|---|
| `pkg_install` | Install packages (auto-detects pip/npm/cargo/go) |

### Directory
| Tool | Description |
|---|---|
| `cd` | Change directory with fuzzy matching |

---

## 🧠 Recommended Models

| Model | Size | VRAM | Speed | Quality |
|---|---|---|---|---|
| `qwen2.5-coder:3b` | ~3B | ~1.9GB | 🚀 Fast | Good (default) |
| `qwen2.5:1.5b` | ~1.5B | ~1GB | ⚡ Fastest | Decent |
| `deepseek-coder:1.3b` | ~1.3B | ~800MB | ⚡ Fastest | Decent |
| `codegemma:2b` | ~2B | ~1.2GB | 🚀 Fast | Good |
| `phi3:3.8b` | ~3.8B | ~2.2GB | 🚀 Fast | Good |
| `qwen2.5-coder:7b` | ~7B | ~4GB | 🐢 Slower | Best |
| `gpt-4o-mini` | Cloud | — | ⚡ Fast | Excellent |

---

## 🔧 Architecture

```
shellmind/
├── pyproject.toml              # Modern PEP 621 packaging
├── src/shellmind/
│   ├── __init__.py             # Package metadata
│   ├── __main__.py             # python -m entry point
│   ├── agent.py                # Agent orchestrator & REPL
│   ├── cli.py                  # CLI argument parsing
│   ├── config.py               # Configuration & defaults
│   ├── memory.py               # Session persistence
│   ├── platform.py             # Cross-platform utilities
│   ├── llm/                    # LLM providers (2 providers)
│   │   ├── base.py             # Abstract provider interface
│   │   ├── ollama.py           # Ollama local provider
│   │   ├── openai.py           # OpenAI/API-compatible provider
│   │   └── model_registry.py   # Auto-detection & switching
│   ├── tools/                  # Tool implementations (18 tools)
│   │   ├── base.py             # BaseTool abstract class
│   │   ├── registry.py         # Tool registry/plugin system
│   │   ├── shell.py            # Shell execution tools
│   │   ├── filesystem.py       # File read/write/edit/search
│   │   ├── git.py              # Git integration (5 tools)
│   │   ├── fileops.py          # File copy/move/diff
│   │   ├── pkg_manager.py      # Package management
│   │   └── interactive.py      # Persistent shell sessions
│   └── ui/                     # Terminal UI
│       ├── colors.py           # Legacy color definitions
│       ├── theme.py            # Theme system (dark/light)
│       ├── display.py          # Output formatting & progress
│       ├── spinner.py          # Loading animations
│       └── prompt.py           # Input prompt builder
├── tests/                      # 64+ tests (pytest)
│   ├── test_memory.py
│   ├── test_platform.py
│   ├── test_tools.py
│   ├── test_tools_extended.py
│   └── test_phase3_phase4.py
├── docs/                       # Documentation
│   └── ARCHITECTURE.md
├── .github/
│   ├── workflows/test.yml      # CI on 3 OSes × 4 Python versions
│   ├── ISSUE_TEMPLATE/         # Issue templates
│   └── PULL_REQUEST_TEMPLATE.md
└── docs/
```

---

## 🎨 Themes

```bash
# Dark theme (default)
:theme dark

# Light theme (for light terminals)
:theme light
```

The theme is persisted per-session and the prompt adapts automatically.

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_platform.py -v

# Run tests without pytest installed
python -m pytest tests/ -v
```

64+ tests covering:
- Memory persistence
- Cross-platform process management
- Shell & filesystem tools
- Git, file ops, package tools
- Interactive shell sessions
- Theme switching
- Provider registry & OpenAI provider
- CdTool fuzzy matching

---

## 📋 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history.

---

## 🤝 Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Development setup
- Running tests
- Code style (ruff + mypy)
- Pull request guidelines
- Adding new tools

---

## 📜 License

MIT — do whatever you want with it.

Built with [Ollama](https://ollama.com/) + [Qwen2.5-Coder](https://github.com/QwenLM/Qwen2.5-Coder).
