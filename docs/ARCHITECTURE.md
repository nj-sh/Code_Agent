# ShellMind Architecture

This document describes the internal architecture of ShellMind for developers.

## Overview

ShellMind is a CLI application that connects an LLM (Large Language Model) to your terminal. The LLM plans steps, calls tools (shell commands, file operations, git, etc.), and summarizes results — all in an interactive REPL loop.

```
User Input
    │
    ▼
┌────────────────────┐     ┌──────────────────────┐
│  Direct Command?   │────▶│ cd, :model, :provider │
│  (no LLM)          │     │ :theme, :help, :clear │
└────────┬───────────┘     └──────────────────────┘
         │ LLM route
         ▼
┌──────────────────────────────────────────────────┐
│              Agent Loop                           │
│                                                   │
│  1. User sends task (e.g., "show git status")     │
│  2. LLM receives task + system prompt             │
│  3. LLM outputs plan (think) + tool calls         │
│  4. Agent executes tools via ToolRegistry         │
│  5. Results shown with progress tracking          │
│  6. Results fed back to LLM                       │
│  7. Repeat until summary is emitted               │
│  8. Summary displayed to user                     │
└──────────────────────────────────────────────────┘
```

## Core Components

### 1. Agent (`agent.py`)
The central orchestrator. The `CodeAgent` class:
- Manages the REPL loop (input → process → display)
- Maintains conversation history
- Handles direct commands (cd, :help, :model, etc.)
- Routes LLM tool calls through the `ToolRegistry`
- Tracks progress via `ProgressTracker`

### 2. Tool Registry (`tools/registry.py`)
Plugin system for all executable actions.
- `ToolRegistry` maps tool names → `BaseTool` instances
- Tools are registered in `CodeAgent._setup_tools()`
- When the LLM calls a tool, `dispatch_tool()` routes through the registry
- Adding a new tool = create a `BaseTool` subclass + register it

### 3. LLM Provider Registry (`llm/model_registry.py`)
Plugin system for LLM backends.
- `ProviderRegistry` auto-detects available providers (Ollama, OpenAI)
- `chat()` delegates to the active provider
- `:provider` command switches between providers
- All providers implement `BaseLLMProvider` interface

### 4. Display System (`ui/`)
Terminal UI with theme support.
- `Display` class formats all output (headers, tool calls, results, summaries)
- `ProgressTracker` shows live todo checklist during task execution
- `Theme` class provides dark/light color schemes
- All display methods use `get_active()` theme instead of hardcoded colors

### 5. Platform Layer (`platform.py`)
Cross-platform abstractions.
- `run_command()` — Execute shell commands with process group management
- `run_command_streaming()` — Execute with real-time output
- `is_windows()`, `is_unix()` — Platform detection
- `normalize_path()` — Path normalization for all OSes
- `kill_process_group()` — Cross-platform process termination

## Data Flow

### Agent Loop (detailed)

```
execute_task(user_input)
  │
  ├─ history.append(user)
  ├─ providers.chat(history)         → LLM responds
  ├─ history.append(assistant)
  │
  ├─ extract_summary()?              → if summary found, return it
  │
  ├─ extract_tool_calls()?
  │   └─ _process_response(response)
  │       │
  │       for each tool_call:
  │       ├─ if "think": display.thinking() + extract_plan_steps()
  │       ├─ display.tool_call()
  │       ├─ (manual mode: confirm?)
  │       ├─ dispatch_tool(name, args)
  │       │   ├─ if "cd": _handle_cd()
  │       │   └─ else: tools.dispatch()
  │       ├─ display.tool_result()
  │       ├─ feed result back to history
  │       ├─ providers.chat()         → next LLM response
  │       └─ _process_response()      → recursive
  │
  └─ return summary (or None)
```

## Tool System

### BaseTool interface

```python
class BaseTool(ABC):
    @property
    def name(self) -> str: ...        # Tool identifier
    @property
    def description(self) -> str: ... # For LLM prompt
    def execute(self, **kwargs) -> ToolResult: ...
```

### ToolResult dataclass

```python
@dataclass
class ToolResult:
    success: bool       # Did the tool succeed?
    output: str         # Text output
    duration: float     # Execution time in seconds
    tool: str           # Tool name
    args: dict          # Arguments used
    cancelled: bool     # Was it cancelled (timeout)?
```

## LLM Provider System

### BaseLLMProvider interface

```python
class BaseLLMProvider(ABC):
    @property
    def name(self) -> str: ...
    def is_available(self) -> bool: ...
    def chat(self, messages, temperature, **kwargs) -> LLMResult: ...
```

### Provider lifecycle

1. `ProviderRegistry.__init__()` calls `_auto_detect()`
2. For each provider, check `is_available()` (Ollama server, OpenAI API key)
3. First available provider becomes active
4. User switches with `:provider <name>`
5. All `chat()` calls go through `registry.chat()`

## Session Persistence

- `Memory` class loads/saves `memory.json`
- Stores: model name, conversation history (~80 messages), last task/summary
- Atomic saves (writes to `.tmp` file, then replaces original)
- Path: `~/.config/shellmind/memory.json` (XDG) or `%APPDATA%/shellmind/memory.json` (Windows)

## Direct Commands

Commands handled without going through the LLM:

| Command | Handler | Effect |
|---|---|---|
| `cd <path>` | `_handle_cd()` | Changes directory with fuzzy matching |
| `go to <path>` | `_handle_cd()` | Same as cd |
| `:model <name>` | Sets model on active provider | Switches LLM model |
| `:provider <name>` | `providers.active_provider` | Switches LLM backend |
| `:theme <name>` | `set_active()` | Switches UI theme |
| `:auto` / `:manual` | Toggle mode | Auto-execute or confirm tools |
| `:retry` | Re-runs `last_input` | Re-executes last task |
| `:status` | Prints session state | Diagnostic info |
| `:help` | Prints menu | Command reference |
| `:clear` | Clears terminal | Screen management |
| `:exit` | Saves + exits | Clean shutdown |

## Testing Strategy

- **Unit tests**: Test individual tools, memory, platform functions
- **No network required**: All tests work offline
- **Temp directories**: File operations use `tempfile.TemporaryDirectory`
- **Cross-platform**: Tests verify Windows/Unix behavior
- **Theme tests**: Verify color scheme switching
- **Provider tests**: Verify registry logic, OpenAI key detection

## Version History

See [CHANGELOG.md](../CHANGELOG.md) for full version history.
