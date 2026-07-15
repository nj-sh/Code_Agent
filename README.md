# ⚡ Code Agent v4 — Ollama CLI Coding Agent

> A lightweight, local-first coding agent powered by Ollama models.
> Inspired by Codex CLI & Claude Code — built for private, offline
> AI-assisted development on modest hardware.

![Version](https://img.shields.io/badge/version-4.0-brightgreen)
![Model](https://img.shields.io/badge/model-qwen2.5--coder:3b-blue)
![Python](https://img.shields.io/badge/python-3.8+-yellow)

---

## ✨ Features

- **🧠 Plan → Execute → Summarize** — The agent plans its approach, executes tools one by one, and wraps up with a concise summary
- **🔧 Tool-Based Execution** — Structured tools for `think`, `execute_command`, `read_file`, `write_file`, `edit_file`, and `search_code`
- **🎨 Beautiful Terminal UI** — Colored output, thinking blocks, bordered summaries, and structured command display
- **⚡ Direct Commands** — `cd` (with fuzzy matching), `:model`, `:help`, `:clear` run instantly without LLM overhead
- **🔄 Auto-Retry** — When a command fails, the agent tries a different approach (up to 3 attempts)
- **💾 Persistent Memory** — Session history and model selection survive restarts via `memory.json`
- **📦 Optimized for Small Models** — Concise prompts, low temperature (0.1), and lightweight tool format work great with 1.5B–7B models

---

## 🛠️ Requirements

| Dependency | Purpose |
|---|---|
| **Python 3.8+** | Runtime |
| **Ollama** | Local LLM server |
| **A coder model** | e.g., `qwen2.5-coder:3b` |
| Unix-like environment | Linux, macOS, Termux |

---

## 📦 Installation

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a lightweight coder model
ollama pull qwen2.5-coder:3b

# 3. Clone and run
git clone https://github.com/your-username/code-agent.git
cd code-agent
python3 Agent.py
```

---

## 🎮 Usage

```
╔══════════════════════════════════════════════╗
║          ⚡ Code Agent v4                    ║
╚══════════════════════════════════════════════╝
  Model:  qwen2.5-coder:3b
  CWD:    ~/projects
  Memory: memory.json
───────────────────────────────────────────────────
~/projects [1.2k] ❯
```

### Example Session
### Command-line options

Run a task once (useful in scripts or editor integrations):

```bash
python3 Agent.py -C ~/project -p "find all TODO comments"
python3 Agent.py "list the files in this directory"
```

Useful options:

| Option | Purpose |
|---|---|
| `-p`, `--prompt TEXT` | Run one task and exit |
| `-C`, `--cwd DIR` | Start in a project directory |
| `-m`, `--model NAME` | Use a model for the current session |
| `--manual` | Ask before every tool call |
| `--no-clear` | Preserve existing terminal output |
| `--help`, `--version` | Show CLI help or version |



```
~/projects [1.2k] ❯ find all python files and count lines

┌ 💭 Thinking ────────────────────────────────┐
│ I'll find .py files first, then count lines │
└─────────────────────────────────────────────┘

🔧 execute_command (command=find . -name "*.py")
  ✓ Done (0.05s)
    ./main.py
    ./utils/helpers.py

🔧 execute_command (command=wc -l **/*.py)
  ✓ Done (0.02s)
    150 total

┌────────────────────────────────────────────┐
│ ✅ **Task Complete**                       │
│ • Found 3 Python files                     │
│ • 150 lines of code total                  │
└────────────────────────────────────────────┘
```

### Commands

| Input | What happens |
|---|---|
| `list files in this directory` | LLM plans and executes `ls -la` |
| `cd Downloads` | Fuzzy-finds and changes directory instantly |
| `create a script that greets the user` | LLM creates, writes, and may test the file |
| `find all TODO comments` | Searches code with ripgrep/grep |
| `:model deepseek-coder:1.3b` | Switches to a different Ollama model |
| `:help` | Shows help menu |
| `:clear` | Clears the screen |
| `exit` | Saves session and quits |

---

## 🧠 Recommended Models

Code Agent is optimized for lightweight Ollama models. Here are good choices:

| Model | Size | VRAM | Speed | Quality |
|---|---|---|---|---|
| `qwen2.5-coder:3b` | ~3B | ~1.9GB | 🚀 Fast | Good (default) |
| `qwen2.5:1.5b` | ~1.5B | ~1GB | ⚡ Fastest | Good |
| `stable-code:3b` | ~3B | ~1.8GB | 🚀 Fast | Good |
| `deepseek-coder:1.3b` | ~1.3B | ~800MB | ⚡ Fastest | Good |
| `codegemma:2b` | ~2B | ~1.2GB | 🚀 Fast | Good |
| `qwen2.5-coder:7b` | ~7B | ~4GB | 🐢 Slower | Best |

Switch models anytime with `:model <name>`.

---

## 🔧 How It Works

```
User Input
    │
    ▼
┌──────────────┐     ┌─────────────────┐
│  Direct?     │────▶│ cd, :model,     │
│  (no LLM)    │     │ :help, :clear   │
└──────┬───────┘     └─────────────────┘
       │ LLM route
       ▼
┌──────────────────────────────────────────┐
│  Agentic Loop                            │
│                                          │
│  1. LLM thinks & plans (think tool)      │
│  2. LLM outputs tool calls               │
│     <tool_call>{"name":"execute_command",│
│       "args":{"command":"ls -la"}}</>    │
│  3. Agent executes tool, captures result │
│  4. Result fed back to LLM               │
│  5. Repeat until summary is emitted      │
│     <summary>✅ Done...</summary>        │
│  6. Summary displayed to user            │
└──────────────────────────────────────────┘
```

### Available Tools

| Tool | Purpose |
|---|---|
| `think` | Internal reasoning and planning |
| `execute_command` | Run any bash command |
| `read_file` | Read a file's contents |
| `write_file` | Create or overwrite a file |
| `edit_file` | Make targeted string replacements |
| `search_code` | Search patterns with ripgrep/grep |

---

## 🗂️ Project Structure

```
code-agent/
├── Agent.py        # Main agent (v4.0)
├── memory.json     # Persistent session memory
└── README.md       # This file
```

---

## 🐛 Troubleshooting

### "Ollama unreachable"
```bash
# Make sure Ollama is running
ollama serve
```

### Model not found
```bash
ollama pull qwen2.5-coder:3b
```

### Permission denied on commands
Some commands may need elevated permissions. The agent will report the error and suggest alternatives.

---

## 📜 License

MIT — do whatever you want with it.

## 🙏 Credits

Built with [Ollama](https://ollama.com/) + [Qwen2.5-Coder](https://github.com/QwenLM/Qwen2.5-Coder).
Inspired by OpenAI Codex CLI and Anthropic Claude Code.
