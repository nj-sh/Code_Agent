# Changelog

All notable changes to ShellMind are documented here.

## [5.0.0] — 2026-07-15

### Added (Phase 5 — Polish & Release)
- Comprehensive README with full feature documentation
- CONTRIBUTING.md with development setup and guidelines
- CHANGELOG.md (this file)
- GitHub issue templates (bug report + feature request)
- GitHub PR template
- docs/ARCHITECTURE.md for developer documentation
- Finalized pyproject.toml for PyPI release

### Added (Phase 4 — Multi-LLM Support)
- **OpenAI provider** — `llm/openai.py` communicates with OpenAI API
- **Provider registry** — `llm/model_registry.py` auto-detects Ollama ↔ OpenAI
- `:provider <name>` command for runtime provider switching
- `:status` now shows active provider

### Added (Phase 3 — Tool Expansion)
- **Git integration** — `git_status`, `git_log`, `git_diff`, `git_commit`, `git_branch` tools
- **File operations** — `copy_file`, `move_file`, `diff_files` tools
- **Package management** — `pkg_install` with auto-detection (pip/npm/cargo/go)
- **Interactive shell** — `shell_send`/`shell_close` for persistent shell sessions
- **18 total tools** registered in ToolRegistry

### Added (Phase 2 — Agent Loop & UI Overhaul)
- **Progress tracking** — Live todo checklist during task execution
- **Theme support** — Dark theme (default) and light theme, switchable via `:theme`
- `:retry` command to re-run the last task
- `:status` command to show session state
- Prompt now respects the active theme
- 33 tests (expanded from 20)

### Added (Phase 1 — Foundation & Cross-Platform)
- **Project renamed** from "Code Agent" to "ShellMind"
- **Modular package structure** — `src/shellmind/` with submodules
- **Cross-platform process management** — `platform.py` replaces Unix-only APIs
- **Fixed `cd` command** — Now works cross-platform with fuzzy matching
- **PyPI-ready packaging** — `pyproject.toml` with PEP 621
- **CI/CD** — GitHub Actions across 3 OSes × 4 Python versions
- **20 tests** with pytest

### Changed
- Agent loop now dispatches through ToolRegistry instead of inline methods
- Colors migrated to Theme system (backward-compatible)
- Git tools use subprocess args lists (no shell injection)

### Removed
- Monolithic `Agent.py` (replaced by modular package)
- `Check.py` (diagnostics integrated into platform module)
- `requirements.txt` (replaced by pyproject.toml)
- Unix-only APIs (`os.setsid`, `signal.SIGKILL`, `os.killpg`)

## [4.0] — 2026-06-01

- Initial release as "Code Agent"
- Single-file Agent.py (~700 lines)
- Ollama-only provider
- Unix-only (Linux/macOS)
- 0 tests
- Basic tool-based execution (plan → execute → summarize)
