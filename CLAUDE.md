# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AdbAutoPlayer is a cross-platform desktop app for automating Android game tasks via ADB (Android Debug Bridge). It uses a **Tauri 2 + SvelteKit + Python** stack: Rust handles the desktop shell and IPC, Python runs the automation engine, and Svelte renders the UI.

---

## Commands

### Frontend (SvelteKit + TypeScript)

```bash
pnpm install           # Install dependencies
pnpm dev               # Dev server on port 1420 (frontend only)
pnpm build             # Build frontend
pnpm check             # Svelte-check + TypeScript type checking
pnpm prettier-write    # Format with Prettier + Tailwind plugin
```

### Python

```bash
uv sync                              # Sync dependencies from uv.lock
uv run pytest                        # Run all tests
uv run pytest tests/path/test_file.py::test_name  # Run single test
uv run pytest --cov --cov-branch     # Run tests with coverage
uv run ruff check --fix              # Lint and auto-fix
uv run ruff format                   # Format code
```

### Rust

```bash
cargo fmt --all                      # Format
cargo clippy --all                   # Lint
```

### Full App (Tauri)

```bash
pnpm tauri dev                       # Run full app (Python + Svelte + Tauri window)
pnpm tauri build                     # Bundle distributable (embeds Python)
```

### Pre-commit (runs all linters)

```bash
uvx pre-commit run --all-files
```

---

## Architecture

### Three-Layer Stack

```
SvelteKit UI (TypeScript)
    ↕ PyTauri IPC (async JSON-RPC, events)
Tauri Runtime (Rust) — window, tray, updater, process lifecycle
    ↕ Embedded Python interpreter (PyO3)
Python Automation Engine
    ↕ ADB (adbutils)
Android Device
```

### Frontend (`src/`)

- `src/lib/form/` — Dynamic JSON Schema form renderer; game settings are rendered entirely from Pydantic model schemas, not hardcoded components.
- `src/lib/stores.ts` — Global Svelte stores for app state (selected game, profile, running task, logs).
- `src/client/` — Auto-generated TypeScript client from PyTauri IPC definitions. **Do not edit manually.**
- SvelteKit is configured as a static SPA (no SSR); all routing is client-side for Tauri compatibility.

### Rust (`src-tauri/src/`)

- Thin command layer that delegates to Python via PyTauri plugin.
- Handles window management, system tray, and the auto-updater.
- Commands defined in `commands.rs` map directly to Python callables.

### Python (`src-tauri/src-python/adb_auto_player/`)

| Module | Role |
|---|---|
| `game.py` | Abstract `Game` base class (~1000 LOC). All tap/swipe/OCR/template-match helpers live here. |
| `games/` | Concrete game implementations (e.g., `afk_journey/base.py` ~27K LOC). Each subclasses `Game`. |
| `device/adb/` | `AdbController` and `DeviceStream` — wraps adbutils for input injection and screen capture. |
| `ocr/` | OCR via RapidOCR + ONNX runtime. |
| `template_matching/` | OpenCV template matching with confidence scoring. |
| `models/` | Pydantic models for device info, geometry (`Point`, `Coordinates`), IPC payloads. |
| `registries/` | `GAME_REGISTRY` and `CUSTOM_ROUTINE_REGISTRY` — games and routines are auto-discovered at runtime. |
| `file_loader/` | TOML-based settings with per-profile support. Settings live in `src-tauri/Settings/`. |
| `ipc/` | IPC data models (`GameGUIOptions`, `LogMessage`) shared between Python and the frontend. |
| `tauri_context/` | Helpers that bridge Python game metadata into UI-renderable form structures. |
| `main_cli.py` | Entry point for standalone CLI mode (no Tauri window). |

### Settings System

- Per-profile TOML files under `src-tauri/Settings/{profile_index}/`.
- Pydantic models validate and document all settings.
- Changing a setting model in Python automatically updates the JSON Schema the frontend renders — no frontend code change needed.

### Game Extension Pattern

To add a new game: subclass `Game`, register it in `GAME_REGISTRY` via the auto-discovery mechanism (`load_modules` + `discover_and_add_games`), and add a TOML settings template. The registry drives all UI menus and task dispatch automatically.

### IPC & Real-Time Logging

- Tasks run in separate Python processes; logs are streamed to the UI via PyTauri `Emitter` events (`log-message`, `task-completed`).
- `CacheGroup` enum controls profile-aware cache invalidation to prevent async race conditions.

---

## Key Configuration Files

| File | Purpose |
|---|---|
| `src-tauri/tauri.conf.json` | Tauri app config (window, updater, capabilities) |
| `src-tauri/pyproject.toml` | Python package config + entry point |
| `pyproject.toml` (root) | uv workspace + Ruff/Pyright tool config |
| `Cargo.toml` (root) | Rust workspace + release profile (LTO thin) |
| `vite.config.ts` | Vite config (dev server port 1420) |
| `.pre-commit-config.yaml` | Git hook pipeline: isort → Ruff → ty → Clippy → Prettier → svelte-check |
