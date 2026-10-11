# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. It holds only repo-wide rules; area-specific notes live in nested `CLAUDE.md` files (loaded when working in that directory) and multi-step procedures live in `.claude/skills/`.

## Shell and Tool Rules

- **File listing**: use the `Glob` tool, never `dir` or `ls` in shell
- **File search**: use the `Grep` tool, never `grep` or `rg` in shell
- **Bash tool on Windows**: runs Git Bash — `dir` does not exist, use `ls` if a shell command is truly needed; prefer forward slashes in paths
- **Glob paths**: always use absolute paths with forward slashes (e.g. `f:/Adbautoplayer/AdbAutoPlayer/src-tauri/...`) or patterns relative to the workspace root; backslashes break glob matching
- **Ruff**: run as `uvx ruff check --fix` and `uvx ruff format` from the repo root `f:\Adbautoplayer\AdbAutoPlayer` — not from `src-tauri/` and not via `uv run ruff`
- **Modules vs packages**: a Python module may be a package directory, not a `.py` file. `decorators` → `decorators/__init__.py` + `decorators/register_command.py`. When asked to read a module, use `Glob` first to check if it's a file or a directory before assuming a path like `decorators.py`
- **CJK / Korean strings**: the `Edit` tool may fail to match `old_string` containing CJK/Korean text. Use a small inline Python script (`content.replace(old, new)`) or anchor `old_string` to surrounding ASCII-only context.

## Markdown Rules (for editing any CLAUDE.md or SKILL.md)

- **Fenced code blocks**: always specify a language — ` ```python `, ` ```bash `, ` ```text `, ` ```toml `. Never use bare ` ``` `.
- **Ordered lists + code blocks**: avoid embedding code blocks inside a numbered list. Use bullet points (`-`) for steps and place code blocks between them as standalone blocks.
- **Headings**: always one blank line above and below every `##` / `###` heading.
- **Lists**: always one blank line above and below every list block.

## Project Overview

AdbAutoPlayer is a cross-platform desktop app for automating Android game tasks via ADB. Stack: **Tauri 2 + SvelteKit + Python** — Rust handles the desktop shell, Python runs the automation engine, Svelte renders the UI.

```text
SvelteKit UI (TypeScript)                       src/
    ↕ PyTauri IPC (async JSON-RPC, events)
Tauri Runtime (Rust) — window, tray, updater    src-tauri/src/
    ↕ Embedded Python interpreter (PyO3)
Python Automation Engine                        src-tauri/src-python/adb_auto_player/
    ↕ ADB (adbutils)
Android Device
```

Nested guides: [src/CLAUDE.md](src/CLAUDE.md), [src-tauri/src/CLAUDE.md](src-tauri/src/CLAUDE.md), [src-tauri/src-python/adb_auto_player/CLAUDE.md](src-tauri/src-python/adb_auto_player/CLAUDE.md), [games/afk_journey/CLAUDE.md](src-tauri/src-python/adb_auto_player/games/afk_journey/CLAUDE.md), [src-tauri/src-python/tests/CLAUDE.md](src-tauri/src-python/tests/CLAUDE.md).

Project skills (`.claude/skills/`): `adb-screenshot` (manual capture on MuMuPlayer multi-display), `debug-guild-scan`, `release-bump`.

## Commands

### Frontend

```bash
pnpm install           # Install dependencies
pnpm dev               # Dev server on port 1420 (frontend only)
pnpm build             # Build frontend
pnpm check             # Svelte-check + TypeScript type checking
pnpm prettier-write    # Format with Prettier + Tailwind plugin
```

### Python

> **IMPORTANT**: `uv run ruff` fails (`ruff` not found in venv). Always use `uvx ruff` from the repo root.

Run Python commands from `src-tauri/` (where `pyproject.toml` lives):

```bash
uv sync                              # Sync dependencies from uv.lock
uv run pytest                        # Run all tests
uv run pytest tests/path/test_file.py::test_name  # Run single test
uv run pytest --cov --cov-branch     # Run tests with coverage
uvx ruff check --fix                 # Lint and auto-fix (run from repo root, NOT src-tauri/)
uvx ruff format                      # Format code (run from repo root)
```

### Rust

```bash
cargo fmt --all                      # Format
cargo clippy --all                   # Lint
```

### Full App and Pre-commit

```bash
pnpm tauri dev                       # Run full app (Python + Svelte + Tauri window)
pnpm tauri build                     # Bundle distributable (embeds Python)
uvx pre-commit run --all-files       # isort → Ruff → ty → Clippy → Prettier → svelte-check
```

## Settings System

- Default/template TOML files (seed values for new profiles) live in `src-tauri/settings/` (**lowercase** — `ADB.toml`, `AFKJourney.toml`, `App.toml`).
- Actual per-profile runtime settings are written by the Rust `save_settings` command to `{app_config_dir}/{profile_index}/*.toml` — **not** under `src-tauri/`. `SettingsLoader.set_app_config_dir()` points Python at this directory on every task/command invocation (see `tauri_profile_aware_command` in `__main__.py`).
- Pydantic models validate and document all settings. Changing a setting model in Python automatically updates the JSON Schema the frontend renders — no frontend code change needed.

## Python Linting Rules

Ruff: `line-length = 88`, `target-version = py312`, Google-style docstrings. Pyright is configured in the root `pyproject.toml` (excludes `node_modules`, `__pycache__`, `pyembed`, `target/`); pre-commit uses `ty` for type checks.

**Banned APIs (will always error):**

- `time.time` → use `time.monotonic()` or `time.perf_counter()`
- `cv2.split` → use numpy indexing: `image[:, :, 0]` instead of `cv2.split(image)[0]`

**Type annotations — modern syntax:** `X | None` not `Optional[X]`, `X | Y` not `Union[X, Y]`, `list[str]` / `dict[str, int]` not `List` / `Dict`.

**Docstrings (Google style) — required on all public functions/classes except in `games/` and `tests/`:**

```python
def my_func(x: int) -> str:
    """Short one-line summary.

    Args:
        x: Description of x.

    Returns:
        Description of return value.

    Raises:
        ValueError: When x is negative.
    """
```

- First line on same line as the opening `"""` (D212 style); no dashes under section names (D407 ignored).

**Magic values (PLR2004):** no bare literals in comparisons — use a module constant (`_MAX_RETRIES = 5`; `if count > _MAX_RETRIES:`).

**Naming (N rules):** classes `PascalCase`; functions/methods/variables `snake_case`; module-level constants `UPPER_SNAKE_CASE`; private members `_leading_underscore`. **N806**: locals inside functions must be `snake_case` even if they feel like constants.

**Per-file relaxed rules:**

- `games/**/*.py` — D101, D102, D103 ignored
- `tests/**/*.py` — D101–D103, PLR0913, PLR2004 ignored
- `__main__.py` — D101–D103, PLW0603 ignored

## Debugging Workflow

Before editing code based on an initial diagnosis, confirm the root cause —
especially for timing, detection, or emulator bugs where the obvious fix is
often wrong (e.g., formation detection was a similarity-threshold issue, not a
crop region; emulator slowness is configurable via `template_timeout`).

- Read all relevant files and logs first.
- List candidate root causes with evidence.
- Present the top hypothesis with supporting code references and wait for user
  confirmation before making any edit.

## Testing

- Run only the test files covering the changed code, never the full suite —
  not even at the end of a task or after a refactor. The full suite takes
  ~6 min and CI (`.github/workflows/python-tests.yml`) already runs it.
- For every bug fix, add a regression test covering the changed branch.
- Never declare a task complete without showing the pass count of the
  targeted test files.

```bash
# from src-tauri/
uv run pytest src-python/tests/path/to/test_file.py -q
```

## Changelog & Release

- Keep changelog entries focused: only include changes the user confirmed.
- Do **not** auto-add `Dependencies`, `type-fix`, or internal-noise sections
  unless the user asks for them.
- When bumping a version, draft the changelog and show it to the user for
  approval before committing. Full procedure: `release-bump` skill.

## GitHub Issues

- When fixing a GitHub issue, read the **full** issue body **and all comments**
  before proposing a fix.
- Check whether the reporter or another contributor already suggested an
  approach and consider it first.

## Key Configuration Files

| File | Purpose |
| --- | --- |
| `src-tauri/tauri.conf.json` | Tauri app config (window, updater, capabilities) |
| `src-tauri/pyproject.toml` | Python package config + entry point |
| `pyproject.toml` (root) | uv workspace + Ruff/Pyright tool config |
| `Cargo.toml` (root) | Rust workspace + release profile (LTO thin) |
| `vite.config.ts` | Vite config (dev server port 1420) |
| `.pre-commit-config.yaml` | Git hook pipeline: isort → Ruff → ty → Clippy → Prettier → svelte-check |
