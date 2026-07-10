# ⚡ CODEX v3.1 — Terminal AI Assistant

> A lightweight, on-device AI coding assistant that works like GitHub Copilot — right in your Termux terminal.
> Powered by **qwen2.5-coder:1.5b** via Ollama.

![Version](https://img.shields.io/badge/version-3.1-brightgreen)
![Model](https://img.shields.io/badge/model-qwen2.5--coder:1.5b-blue)
![Python](https://img.shields.io/badge/python-3.8+-yellow)

---

## ✨ Features

- **🤖 LLM-Powered Commands** — Ask in plain English, get bash commands auto-executed
- **⚡ Direct Ops** — `list`, `cd`, `mkdir`, `make a folder` run instantly without LLM overhead
- **🔄 Auto Mode** — AI reads your intent, runs commands, fixes failures, all automatically
- **🔒 Manual Mode** — AI suggests commands, you approve before execution
- **🧠 Context-Aware** — Remembers previous commands and output within session
- **🔍 Smart Directory Search** — Fuzzy-matches `cd` targets across parent directories
- **🧪 Repeat Detection** — Catches hallucination loops and resets automatically
- **🚫 Credential Guard** — Blocks AI from asking for passwords/GitHub tokens unless git-related

---

## 🛠️ Requirements

- **Python 3.8+**
- **Ollama** with `qwen2.5-coder:1.5b` (or any model)
- Unix-like environment (Termux on Android, Linux, macOS)

---

## 📦 Installation

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull the model
ollama pull qwen2.5-coder:1.5b

# 3. Download CODEX
git clone https://github.com/your-username/codex.git
cd codex

# 4. Run it
python3 codex_agent.py
```

---

## 🎮 Usage

```
╔════════════════════════╗
║   ⚡ CODEX v3.1 AI   ║
╚════════════════════════╝
  qwen2.5-coder:1.5b
  Direct: list, cd, mkdir, make a folder
  :auto  :manual  exit
──────────────────────────────────
~ ❯
```

### Examples

| You type | What happens |
|---|---|
| `list folders` | `ls -d */` — runs instantly, no LLM |
| `list all files` | `ls -la` — shows everything |
| `cd Downloads` | Fuzzy-finds and changes directory |
| `make a folder projects` | `mkdir projects` — creates it |
| `show me all python files` | LLM generates `find . -name "*.py"` |
| `delete the temp folder` | LLM decides best approach |
| `:manual` | Switch to manual mode (approve each command) |
| `:auto` | Switch back to auto mode |
| `exit` | Quit |

### Commands

| Command | Action |
|---|---|
| `:auto` or `:a` | Switch to **auto** mode (default) |
| `:manual` or `:m` | Switch to **manual** mode |
| `exit` | Quit CODEX |

---

## 🔧 How It Works

```
┌──────────┐    ┌─────────────┐    ┌──────────┐
│  User    │───▶│ Classifier  │───▶│ Direct?  │──▶ Run command
│  Input   │    │ (greeting,  │    │ (list,   │
│          │    │  command,   │    │  cd,     │
│          │    │  question)  │    │  mkdir)  │
└──────────┘    └──────┬──────┘    └──────────┘
                       │ LLM route
                       ▼
                ┌──────────────┐
                │ Ollama       │
                │ qwen2.5-coder│
                └──────┬───────┘
                       │ bash commands
                       ▼
                ┌──────────────┐     ┌──────────┐
                │ Extractor    │────▶│ Auto     │──▶ Execute + retry
                │ (``` blocks) │     │ Cycle    │    on failure
                └──────────────┘     └──────────┘
```

---

## 🚀 Making It Act Like GitHub Copilot

CODEX v3.1 already behaves like Copilot in these ways:

- ✅ **Context-aware** — it knows your current directory
- ✅ **Auto-executes** — no manual copy-paste of suggested commands
- ✅ **Self-correcting** — retries with a different approach on failure
- ✅ **Concise** — one-sentence explanations, no fluff
- ✅ **In-line output** — shows command results immediately

### Pro Tips

| Goal | How |
|---|---|
| Multi-step tasks | `"find all .py files, count lines, sort by size"` |
| Git workflows | `"commit and push with message 'fixed bug'"` |
| File editing | `"add a shebang to script.sh"` |
| Debugging | `"my script crashes, show me the error lines"` |

---

## 🐛 Troubleshooting

### "Ollama unreachable"
```bash
# Make sure Ollama is running
ollama serve
```

### Model not found
```bash
ollama pull qwen2.5-coder:1.5b
```

### Change model
Edit `MODEL_NAME` in `codex_agent.py`:
```python
MODEL_NAME = "codellama:7b"  # or your preferred model
```

---

## 📁 Project Structure

```
codex/
├── codex_agent.py    # Main assistant (v3.1)
├── README.md         # This file
└── Github/           # (your repos)
```

---

## 🧠 Model Notes

- **Default:** `qwen2.5-coder:1.5b` — fast, ~1GB RAM, good for mobile
- **Upgrades:** `codellama:7b` (smarter, ~4GB), `deepseek-coder:6.7b`
- **Temperature:** 0.1 (deterministic — same input → same output)

---

## 📜 License

MIT — do whatever you want with it.

---

## 🙏 Credits

Built with [Ollama](https://ollama.com/) + [Qwen2.5-Coder](https://github.com/QwenLM/Qwen2.5-Coder) on Termux.
