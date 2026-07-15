<p align="center">
  <h1 align="center">🧠 ShellMind</h1>
  <p align="center"><i>Cross-Platform AI Coding Assistant for Your Terminal</i></p>
  <p align="center">
    <a href="https://github.com/shellmind/shellmind"><img src="https://img.shields.io/badge/version-5.0.0-blue?style=flat-square" alt="Version"></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-yellow?style=flat-square" alt="Python"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License"></a>
    <a href="https://github.com/shellmind/shellmind/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/shellmind/shellmind/test.yml?branch=main&label=tests&style=flat-square" alt="Tests"></a>
    <img src="https://img.shields.io/badge/OS-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat-square" alt="OS">
    <img src="https://img.shields.io/badge/tests-64%20passing-brightgreen?style=flat-square" alt="64 tests">
  </p>
</p>

---

## ⚡ Quick Start

```bash
# 1. Clone and install
git clone https://github.com/nj-sh/Code_Agent.git
cd Code_Agent
pip install -e .

# 2. Pull a local AI model (optional — use any Ollama model)
ollama pull qwen2.5-coder:3b

# 3. Run it!
shellmind
```

**No pip? No problem — run directly:**
```bash
python -m shellmind
```

---

## 🎯 What ShellMind Does

ShellMind is an **AI agent for your terminal**. Describe a task in plain English, and it plans, executes, and summarizes — just like a pair programmer.

```
~/projects [1.2k] A > show git status and recent commits

  Outgoing: [1/2]                                                                                                                                                                
  ├-[~] Check git status                                                                                                                                                        
  └-[ ] Show recent commits

>> git_status
  ✓ Done (0.05s)
    On branch: main
    M src/shellmind/agent.py

>> git_log (count=5)
  ✓ Done (0.03s)
    a1b2c3d Fix agent loop edge case
    e4f5g6h Add theme support

┌────────────────────────────────────────────────────────────────┐
│ ✓ **Task Complete**                                            │
│ • Showed git status with 1 modified file                       │
│ • Listed 2 recent commits                                      │
└────────────────────────────────────────────────────────────────┘
```

---

## ✨ Features at a Glance

| Capability | Details |
|---|---|
| **🤖 18 Built-in Tools** | Shell, filesystem, git, file ops, package mgmt, and more |
| **🪟 Cross-Platform** | Windows, Linux, macOS — same experience everywhere |
| **🔄 Multi-LLM** | Ollama (local) + OpenAI (cloud) — switch with `:provider` |
| **🎨 Themed UI** | Dark/light themes switchable at runtime |
| **📋 Progress Tracking** | Live todo checklist shows what the AI is doing |
| **💾 Persistent Memory** | Remembers context between sessions |
| **📦 Zero Dependencies** | Pure Python standard library only |

---

## 📖 Usage

### Talk to the AI

| Say this | It does |
|---|---|
| `list files in this directory` | Runs `ls` / `dir` |
| `create a python script` | Writes and tests a file |
| `find all TODO comments` | Searches your code |
| `show git status and recent commits` | Uses git tools |
| `install flask` | Detects pip and installs |
| `diff old.py new.py` | Shows file differences |

### Direct Commands (instant, no AI)

| Command | Purpose |
|---|---|
| `cd <path>` / `go to <path>` | Change directory with fuzzy matching |
| `:model <name>` | Switch AI model |
| `:provider <name>` | Switch provider (ollama, openai) |
| `:theme <name>` | Switch UI theme (dark, light) |
| `:quiet` / `:verbose` / `:debug` | Control output verbosity |
| `:undo` | Undo last file edit |
| `:retry` | Re-run the last task |
| `:cancel` | Stop the current task |
| `:manual` / `:auto` | Toggle tool confirmation |
| `:help` | Show all commands |

### One-shot mode

```bash
shellmind -p "find all TODO comments"
shellmind -C ~/project -p "show git status"
```

---

## 🧠 LLM Providers

| Provider | Switch with | Setup |
|---|---|---|
| **Ollama** (default) | `:model qwen2.5-coder:3b` | `ollama serve` |
| **OpenAI** | `:provider openai` | Set `OPENAI_API_KEY` |

```bash
# Switch between providers at runtime
:model deepseek-coder:1.3b          # Use a different Ollama model
:provider openai                    # Switch to OpenAI
:model gpt-4o-mini                  # Pick an OpenAI model
:provider ollama                    # Switch back to local
```

### Recommended Models

| Model | Size | VRAM | Quality |
|---|---|---|---|
| `qwen2.5-coder:3b` | ~3B | ~1.9GB | Good *(default)* |
| `deepseek-coder:1.3b` | ~1.3B | ~800MB | Decent, fast |
| `qwen2.5-coder:7b` | ~7B | ~4GB | Best |
| `gpt-4o-mini` | — | Cloud | Excellent |

---

## 🏗️ Project Structure

```
Code_Agent/
├── pyproject.toml            # Python package (pip install)
├── src/shellmind/            # The agent
│   ├── agent.py              # Main loop & REPL
│   ├── cli.py                # CLI entry point
│   ├── platform.py           # Cross-platform utilities
│   ├── llm/ (ollama, openai) # LLM providers
│   ├── tools/ (18 tools)     # All actions the AI can take
│   └── ui/ (themes, display) # Terminal UI
├── tests/                    # 64 tests
└── docs/                     # Documentation
```

---

## 🧪 Tests

```bash
python -m pytest tests/ -v    # All 64 tests pass
```

---

## 📜 License

MIT — do whatever you want.

Built with [Ollama](https://ollama.com/) + [Qwen2.5-Coder](https://github.com/QwenLM/Qwen2.5-Coder).
