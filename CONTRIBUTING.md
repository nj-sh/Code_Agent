# Contributing to ShellMind

Thanks for considering contributing! ShellMind is a community-driven open-source project, and we welcome contributions of all kinds.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Adding a New Tool](#adding-a-new-tool)
- [Adding a New LLM Provider](#adding-a-new-llm-provider)
- [Testing](#testing)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

Be respectful, inclusive, and constructive. We're all here to learn and build something awesome together.

## Development Setup

### Prerequisites

- Python 3.10+
- Git
- (Optional) Ollama for local LLM testing

### Setup

```bash
# Clone the repository
git clone https://github.com/shellmind/shellmind.git
cd shellmind

# Install in editable mode
pip install -e .

# Install development dependencies
pip install pytest ruff mypy

# Verify setup
shellmind --help
python -m pytest tests/ -v
```

### Running without install

```bash
python -m shellmind --help
PYTHONPATH=src python -m shellmind
```

## Project Structure

```
src/shellmind/
├── agent.py              # Main agent orchestrator & REPL loop
├── cli.py                # CLI argument parsing
├── config.py             # Configuration constants
├── memory.py             # Session persistence
├── platform.py           # Cross-platform utilities
├── llm/
│   ├── base.py           # BaseLLMProvider interface
│   ├── ollama.py         # Ollama provider
│   ├── openai.py         # OpenAI provider
│   └── model_registry.py # Provider discovery & switching
├── tools/
│   ├── base.py           # BaseTool abstract class + ToolResult
│   ├── registry.py       # ToolRegistry for plugin system
│   ├── shell.py          # Shell execution tools
│   ├── filesystem.py     # Read/write/edit/search
│   ├── git.py            # Git integration
│   ├── fileops.py        # File copy/move/diff
│   ├── pkg_manager.py    # Package management
│   └── interactive.py    # Persistent shell sessions
└── ui/
    ├── colors.py         # ANSI color definitions
    ├── theme.py          # Theme system (dark/light)
    ├── display.py        # Output formatting + ProgressTracker
    ├── spinner.py        # Loading animations
    └── prompt.py         # Input prompt builder
```

## Adding a New Tool

Tools are the core of ShellMind's functionality. Here's how to add one:

### 1. Create the tool class

In the appropriate file under `src/shellmind/tools/`, create a class that inherits from `BaseTool`:

```python
from shellmind.tools.base import BaseTool, ToolResult

class MyNewTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"  # Used in LLM tool calls

    @property
    def description(self) -> str:
        return "What my tool does. Args: `arg1`, `arg2`"

    def execute(self, **kwargs) -> ToolResult:
        t0 = time.time()
        arg1 = kwargs.get("arg1", "")
        # ... tool logic ...
        return ToolResult(success=True, output="result", duration=time.time() - t0, tool=self.name, args=kwargs)
```

### 2. Add an aggregator class

```python
class MyToolSet:
    def __init__(self):
        self.my_tool = MyNewTool()

    def get_all(self) -> list[BaseTool]:
        return [self.my_tool]
```

### 3. Register in the tool registry

In `src/shellmind/tools/__init__.py`, export your new aggregator class.

Then in `src/shellmind/agent.py`, add `MyToolSet().get_all()` to `_setup_tools()`, and add the tool to the system prompt.

### 4. Add tests

Create tests in `tests/` that cover:
- Tool registration
- Success cases
- Error cases (missing args, invalid input)
- Edge cases

### 5. Document

Add the tool to the table in README.md.

## Adding a New LLM Provider

### 1. Create the provider class

In `src/shellmind/llm/`, create a class that inherits from `BaseLLMProvider`:

```python
from shellmind.llm.base import BaseLLMProvider, LLMResult

class MyProvider(BaseLLMProvider):
    @property
    def name(self) -> str:
        return "my_provider"

    def is_available(self) -> bool:
        # Check API key, server status, etc.
        return bool(os.environ.get("MY_API_KEY"))

    def chat(self, messages, temperature=0.1, **kwargs) -> LLMResult:
        # ... API call logic ...
        return LLMResult(success=True, content="response", ...)
```

### 2. Register in the provider registry

In `src/shellmind/llm/__init__.py`, export your provider.
In `src/shellmind/llm/model_registry.py`, add auto-detection:

```python
my_prov = MyProvider()
self.register(my_prov)
if my_prov.is_available() and self._active is None:
    self._active = my_prov.name
```

### 3. Add tests

Test at minimum: instantiation, `is_available()` without credentials, interface conformance.

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific tests
python -m pytest tests/test_tools_extended.py -v

# Run with coverage (requires pytest-cov)
python -m pytest tests/ --cov=src/shellmind/
```

All tests use **no external dependencies** (no Ollama server needed). Tests that need filesystem operations use `tempfile.TemporaryDirectory`.

### Writing tests

- Use `tempfile.TemporaryDirectory` for filesystem tests
- Test both success and failure modes
- Test cross-platform behavior when applicable
- Don't require network access (Ollama, API keys)

## Code Style

ShellMind uses **[ruff](https://github.com/astral-sh/ruff)** for linting and **mypy** for type checking.

```bash
# Lint
ruff check src/ tests/

# Type check (best-effort, strict mode not enforced yet)
mypy src/ tests/ || true

# Format (coming soon: ruff format)
```

### Style guidelines

- Line length: 88 characters
- Use type hints for all function signatures
- Use dataclasses for data containers
- Use `pathlib.Path` for file paths
- Use `from shellmind.ui.theme import get_active` for colors (not legacy `C`)
- Use `from shellmind.platform import is_windows` for platform-specific code
- Keep functions focused and under 50 lines where possible

## Pull Request Process

1. **Fork** the repository and create a branch from `main`
2. **Implement** your changes with tests
3. **Run** the test suite: `python -m pytest tests/ -v`
4. **Lint** your code: `ruff check src/ tests/`
5. **Update** documentation (README, CHANGELOG) if needed
6. **Submit** a PR with a clear title and description

### PR template

When submitting, include:
- What your change does
- Why it's needed
- How you tested it
- Any breaking changes

## Issue Templates

- **Bug report**: Describe the issue, steps to reproduce, expected vs actual behavior, environment (OS, Python version, model)
- **Feature request**: Describe the feature, use case, and any implementation ideas

## Release Process

1. Update version in `src/shellmind/__init__.py` and `src/shellmind/config.py`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Build: `python -m build`
5. Publish: `python -m twine upload dist/*`
6. Tag the release: `git tag v5.x.x && git push --tags`

---

Thank you for contributing! 🚀
