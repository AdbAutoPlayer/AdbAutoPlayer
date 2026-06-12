# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Shell and Tool Rules

- **File listing**: use the `Glob` tool, never `dir` or `ls` in shell
- **File search**: use the `Grep` tool, never `grep` or `rg` in shell
- **Bash tool on Windows**: runs Git Bash — `dir` does not exist, use `ls` if a shell command is truly needed; prefer forward slashes in paths
- **Glob paths**: always use absolute paths with forward slashes (e.g. `f:/Adbautoplayer/AdbAutoPlayer/src-tauri/...`) or patterns relative to the workspace root; backslashes break glob matching
- **Ruff**: run as `uvx ruff check --fix` and `uvx ruff format` from the repo root `f:\Adbautoplayer\AdbAutoPlayer` — not from `src-tauri/` and not via `uv run ruff`
- **Modules vs packages**: a Python module may be a package directory, not a `.py` file. `decorators` → `decorators/__init__.py` + `decorators/register_command.py`. When asked to read a module, use `Glob` first to check if it's a file or a directory before assuming a path like `decorators.py`

---

## Markdown Rules (for editing this file)

These rules must be followed every time this file is edited to avoid lint warnings:

- **Fenced code blocks**: always specify a language — ` ```python `, ` ```bash `, ` ```text `, ` ```toml `. Never use bare ` ``` `.
- **Ordered lists + code blocks**: avoid embedding code blocks inside a numbered list. Instead, use bullet points (`-`) for steps and place code blocks between them as standalone blocks, or describe the code block in a bullet then show it outside the list.
- **Headings**: always one blank line above and below every `##` / `###` heading.
- **Lists**: always one blank line above and below every list block.

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

> **IMPORTANT**: `uv run ruff` fails (`ruff` not found in venv). Always use `uvx ruff` from the repo root.

Run Python commands from the `src-tauri/` directory (where `pyproject.toml` lives):

```bash
uv sync                              # Sync dependencies from uv.lock
uv run pytest                        # Run all tests
uv run pytest tests/path/test_file.py::test_name  # Run single test
uv run pytest --cov --cov-branch     # Run tests with coverage
uvx ruff check --fix                 # Lint and auto-fix (run from repo root, NOT src-tauri/)
uvx ruff format                      # Format code (run from repo root)
```

Tests mock `pytauri` and `adb_auto_player.ext_mod` (Rust-compiled extensions) so no device or Tauri window is required.

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

```text
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
| --- | --- |
| `game.py` | `Game` base class composed from mixins (`_InputMixin`, `_ScreenshotMixin`, `_TemplateMixin`, `_LifecycleMixin`, `_TaskMixin`). All tap/swipe/OCR/template-match helpers live here. |
| `games/` | Concrete game implementations (e.g., `afk_journey/base.py`). Each subclasses `Game` and uses further mixins for large feature areas. |
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

To add a new game:

1. Create a class under `games/<game_name>/` that subclasses `Game`.
2. Decorate it with `@register_game()` — supplies game metadata and the Pydantic settings class.
3. Decorate task methods with `@register_command()` — wires them into the UI menu with optional labels/tooltips.
4. For alternate task variants, use `@register_custom_routine_choice()` on methods.
5. Add a TOML settings template under `src-tauri/Settings/`.

All three decorator types are required to fully wire a game into the UI. The auto-discovery (`load_modules` + `discover_and_add_games`) picks up any decorated classes automatically — no manual registry edits needed.

### Python Type Checking

Pyright is configured in the root `pyproject.toml`. It excludes `node_modules`, `__pycache__`, `pyembed`, and `target/` — the Tauri build copies Python embeddings into `target/`, which would otherwise produce false type errors. The pre-commit pipeline uses `ty` (not Pyright directly) for type checks.

### Linting Rules

Ruff is configured with `line-length = 88`, `target-version = py312`, Google-style docstrings. Run `uv run ruff check --fix && uv run ruff format` from `src-tauri/` before committing.

**Banned APIs (will always error):**

- `time.time` → use `time.monotonic()` or `time.perf_counter()`
- `cv2.split` → use numpy indexing: `image[:, :, 0]` instead of `cv2.split(image)[0]`

**Type annotations — use modern Python 3.10+ syntax:**

- `X | None` not `Optional[X]`
- `X | Y` not `Union[X, Y]`
- `list[str]`, `dict[str, int]` not `List[str]`, `Dict[str, int]`

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

- First line on same line as the opening `"""` (D212 style)
- Blank line before `Args:`, `Returns:`, `Raises:` sections is NOT needed (Google style)
- No dashes under section names (D407 is ignored)

**Magic values — avoid bare literals in comparisons (PLR2004):**

```python
# bad
if count > 5:
# good
_MAX_RETRIES = 5
if count > _MAX_RETRIES:
```

**Naming conventions (N rules):**

- Classes: `PascalCase`
- Functions/methods/variables: `snake_case`
- Module-level constants: `UPPER_SNAKE_CASE`
- Private class attributes/methods: `_leading_underscore`
- **N806**: local variables inside functions must be `snake_case` even if they feel like constants — `UPPER_SNAKE_CASE` is only valid at module level

**Per-file relaxed rules:**

- `games/**/*.py` — D101, D102, D103 ignored (no docstrings required)
- `tests/**/*.py` — D101–D103, PLR0913, PLR2004 ignored
- `__main__.py` — D101–D103, PLW0603 ignored

### IPC & Real-Time Logging

- Tasks run in separate Python processes; logs are streamed to the UI via PyTauri `Emitter` events (`log-message`, `task-completed`).
- `CacheGroup` enum controls profile-aware cache invalidation to prevent async race conditions.

---

## Quick Reference

### Key File Map

```text
# Game engine
src-tauri/src-python/adb_auto_player/game/game.py          # Game base class (public API)
src-tauri/src-python/adb_auto_player/game/_base.py         # Base internals
src-tauri/src-python/adb_auto_player/game/_input_mixin.py  # tap/swipe helpers
src-tauri/src-python/adb_auto_player/game/_template_mixin.py
src-tauri/src-python/adb_auto_player/game/_screenshot_mixin.py
src-tauri/src-python/adb_auto_player/game/_lifecycle_mixin.py
src-tauri/src-python/adb_auto_player/game/_task_mixin.py

# AFK Journey
src-tauri/src-python/adb_auto_player/games/afk_journey/base.py
src-tauri/src-python/adb_auto_player/games/afk_journey/settings.py
src-tauri/src-python/adb_auto_player/games/afk_journey/navigation.py
src-tauri/src-python/adb_auto_player/games/afk_journey/mixins/          # one file per feature
src-tauri/src-python/adb_auto_player/games/afk_journey/mixins/guild_member_scan.py
src-tauri/src-python/adb_auto_player/games/afk_journey/custom_routine/  # custom routines

# OCR
src-tauri/src-python/adb_auto_player/ocr/_backend.py          # abstract backend
src-tauri/src-python/adb_auto_player/ocr/rapidocr_backend.py
src-tauri/src-python/adb_auto_player/ocr/qwen2vl_backend.py   # needs ≥6GB VRAM
src-tauri/src-python/adb_auto_player/ocr/tesseract_backend.py

# Template matching
src-tauri/src-python/adb_auto_player/template_matching/template_matcher.py

# Models
src-tauri/src-python/adb_auto_player/models/geometry/        # Point, Box, Coordinates
src-tauri/src-python/adb_auto_player/models/ocr/ocr_result.py
src-tauri/src-python/adb_auto_player/models/template_matching/

# IPC / UI
src-tauri/src-python/adb_auto_player/ipc/                    # shared Python↔frontend models
src-tauri/src-python/adb_auto_player/registries/registries.py

# Decorators
src-tauri/src-python/adb_auto_player/decorators.py           # register_game, register_command, register_custom_routine_choice

# Settings (TOML templates)
src-tauri/Settings/App.toml
src-tauri/Settings/ADB.toml
src-tauri/Settings/AFKJourney.toml

# Tests
src-tauri/src-python/tests/test_game.py
src-tauri/src-python/tests/test_e2e_flow.py
src-tauri/src-python/tests/games/afk_journey/mixins/test_guild_member_scan.py
src-tauri/src-python/tests/ocr/
src-tauri/src-python/tests/template_matching/
src-tauri/src-python/tests/utils/dummy_game.py  # minimal Game stub for tests
```

---

### Task Recipes

#### Add a command to an existing game (AFK Journey example)

1. Open or create the relevant mixin in `games/afk_journey/mixins/<feature>.py`
2. Add the method with decorators:

```python
from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.decorators import GUIMetadata

class MyFeatureMixin(AFKJourneyBase):
    @register_command(
        name="MyFeature",
        gui=GUIMetadata(
            label="My Feature",
            category=AFKJCategory.GAME_MODES,
            tooltip="Short description shown in the UI",
        ),
    )
    @register_custom_routine_choice(label="My Feature")  # omit if no custom routine needed
    def run_my_feature(self) -> None:
        """Run My Feature."""
        self.start_up(device_streaming=False)
        # implementation here
```

1. Add the mixin to `AFKJourneyBase` in `games/afk_journey/base.py` (check existing pattern).
2. No frontend changes needed — the decorator wires everything automatically.

#### Modify OCR behavior

- **Switch backend**: call `self.ocr_backend` (set on `Game`); override in the mixin if a specific backend is needed.
- **Change model for a scan method**: instantiate `RapidOCRBackend` or `QwenVLOCRBackend` directly.
- **Extract text from a region**:

```python
region = self.get_screenshot().crop((x1, y1, x2, y2))  # PIL crop
results = self.ocr_backend.detect_text(region)           # returns list[OcrResult]
for r in results:
    print(r.text, r.box)
```

- **CJK / special characters**: never rely on `isdigit()` or exact string match; use regex and diacritics stripping. See `guild_member_scan.py` for the pattern.
- **Chest-value regex**: `re.compile(r"^\D{0,3}(\d+)$")` handles `￥8`, `个8`, and plain `8`.

#### Debug a scan (guild scan / ranking)

1. **Capture frames**: screenshots are saved to `C:\Users\sacri\AppData\Roaming\com.AdbAutoPlayer.AdbAutoPlayer\0\data\screenshots\`
2. **Offline test script**: `src-tauri/src-python/scripts/test_activeness_ocr.py` — runs OCR on saved PNGs without a device.
3. **Per-frame debug**: `src-tauri/src-python/scripts/debug_chest_frames.py` — prints pairs found per frame.
4. **Common causes of missing entries**:
   - Swipe too long → inertia skips rows (reduce `ey` or shorten `duration`)
   - `isdigit()` rejects icon-prefixed values → use regex
   - x-position filter too tight → check `_X_CHEST_NAME_MAX` / `_X_CHEST_RANK_BADGE_MAX`
   - Not enough scrolls → increase `_MAX_SCROLLS_*`

---

### Test Structure

#### Mock pattern (required when importing anything that touches pytauri or ext_mod)

```python
# ruff: noqa: E402  ← required when sys.modules patching precedes imports
import sys
from unittest.mock import MagicMock

mock_pytauri = MagicMock()
mock_pytauri.Commands = MagicMock
mock_pytauri.AppHandle = MagicMock
mock_pytauri.Event = MagicMock
mock_pytauri.Emitter = MagicMock

sys.modules["pytauri"] = mock_pytauri
sys.modules["adb_auto_player.ext_mod"] = MagicMock()

# normal imports after this point
from adb_auto_player.games.afk_journey.mixins.my_mixin import MyMixin
```

Only needed if the module under test imports from `pytauri` or `adb_auto_player.ext_mod` (directly or transitively). Most pure-logic tests on mixins don't need it.

#### Minimal game stub for mixin tests

```python
from adb_auto_player.games.afk_journey.mixins.my_mixin import MyMixin

class _Stub(MyMixin):
    """Minimal stub — only pure-logic methods exercised."""

def test_something():
    bot = _Stub()
    result = bot._some_pure_method(...)
    assert result == expected
```

#### Tests that need real images

```python
from pathlib import Path
TEST_DATA_DIR = Path(__file__).parent / "data"  # put PNGs here
```

#### Run a single test

```bash
# from src-tauri/
uv run pytest tests/games/afk_journey/mixins/test_guild_member_scan.py::TestCanonicalizeObservations::test_ranked_observation_wins_over_null_supplements -v
```

---

## Known Quirks / Gotchas

### CJK / Korean characters in OCR and file edits

- The guild scan OCR (`guild_member_scan.py`) handles Korean and CJK member names (e.g. `이른봄날`, `典明`, `旅人`). RapidOCR may output heuristic variants like `弓号言l0` → `이른봄날`; diacritics stripping is applied on both the OCR output and the guild member name before comparison.
- When editing files that contain CJK/Korean strings, the `Edit` tool may fail to match `old_string` due to encoding issues. Workaround: use a small inline Python script (`content.replace(old, new)`) or anchor `old_string` to surrounding ASCII-only context.

### GuildManagerScan (`games/afk_journey/mixins/guild_member_scan.py`)

This is the most complex module in the repo. Key implementation details:

- **Chest contribution OCR**: values appear as `￥8` or `个8` (icon + number) not plain `8`. Use `re.compile(r"^\D{0,3}(\d+)$")` to extract the number, not `isdigit()`.
- **Rank badge vs member name disambiguation**: rank badges are at x≈105; member names at x≈330+. Filter by `box.center.x < _X_CHEST_RANK_BADGE_MAX (200)` to avoid treating a member named "67" as a rank number.
- **Scroll parameters matter**: swipe `sy=1400, ey=1100, duration=1.5` with 2.0s post-swipe sleep. Longer swipes cause the list to skip entries due to inertia.
- **OCR models**: activeness + chest use RapidOCR PP-OCRv5; DR/SA rankings use Qwen2-VL-2B (needs ≥6GB VRAM) with RapidOCR fallback.
- Guild member list is sourced from Supabase API; keep `GUILD_MEMBERS` in test scripts updated when membership changes.

### Auto-generated frontend client

`src/client/` is generated from PyTauri IPC definitions — never edit it manually. Changes to Python IPC models regenerate it.

---

## Key Configuration Files

| File | Purpose |
| --- | --- |
| `src-tauri/tauri.conf.json` | Tauri app config (window, updater, capabilities) |
| `src-tauri/pyproject.toml` | Python package config + entry point |
| `pyproject.toml` (root) | uv workspace + Ruff/Pyright tool config |
| `Cargo.toml` (root) | Rust workspace + release profile (LTO thin) |
| `vite.config.ts` | Vite config (dev server port 1420) |
| `.pre-commit-config.yaml` | Git hook pipeline: isort → Ruff → ty → Clippy → Prettier → svelte-check |
