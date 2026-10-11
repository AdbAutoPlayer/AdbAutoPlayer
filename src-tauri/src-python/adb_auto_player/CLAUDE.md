# Python automation engine (`adb_auto_player`)

## Module Map

| Module | Role |
| --- | --- |
| `game/` | `Game` base class (`game.py`) composed from mixins: `_input_mixin.py` (tap/swipe), `_screenshot_mixin.py`, `_template_mixin.py`, `_lifecycle_mixin.py`, `_task_mixin.py`, `_base.py`. All tap/swipe/OCR/template-match helpers live here. |
| `games/` | Concrete games: `afk_journey/` (largest, most active), `blue_protocol_star_resonance/`, `guitar_girl/`. Each subclasses `Game` and uses further mixins for large feature areas. |
| `device/adb/` | `AdbController` and `DeviceStream` — wraps adbutils for input injection and screen capture (auto-targets the right display on MuMuPlayer multi-display images). |
| `ocr/` | `_backend.py` (abstract), `rapidocr_backend.py`, `qwen2vl_backend.py` (needs ≥6GB VRAM), `tesseract_backend.py`. |
| `template_matching/` | OpenCV template matching with confidence scoring (`template_matcher.py`). |
| `models/` | Pydantic models: `geometry/` (`Point`, `Box`, `Coordinates`), `ocr/ocr_result.py`, `template_matching/`, IPC payloads. |
| `registries/` | `GAME_REGISTRY`, `COMMAND_REGISTRY`, `CUSTOM_ROUTINE_REGISTRY`, `CACHE_REGISTRY` — auto-discovered at runtime. |
| `decorators/` | Package: `register_game.py`, `register_command.py`, `register_custom_routine_choice.py`, `register_lru_cache.py` (exports `register_cache`, profile-aware caching). |
| `file_loader/` | `SettingsLoader` — resolves per-profile settings/resource paths and loads TOML settings. |
| `ipc/` | IPC data models (`GameGUIOptions`, `LogMessage`) shared with the frontend. |
| `tauri_context/` | Bridges game metadata into UI-renderable form structures; holds `profile_aware_cache`. |
| `main_cli.py` | Standalone CLI entry point (no Tauri window). |
| `__main__.py` | PyTauri app entry point — builds `Commands()`, registers `start_task`/`stop_task`/`debug`/etc., implements the multiprocessing task model. |

## Game Extension Pattern

To add a new game:

- Create a class under `games/<game_name>/` that subclasses `Game`.
- Decorate it with `@register_game()` — supplies game metadata and the Pydantic settings class.
- Decorate task methods with `@register_command()` — wires them into the UI menu with optional labels/tooltips.
- For alternate task variants, use `@register_custom_routine_choice()` on methods.
- Add a TOML settings template under `src-tauri/settings/`.

All three decorator types are required to fully wire a game into the UI. Auto-discovery (`load_modules` + `discover_and_add_games`) picks up decorated classes — no manual registry edits.

## OCR Usage

- **Switch backend**: use `self.ocr_backend` (set on `Game`); override in the mixin if a specific backend is needed.
- **Change model for a scan method**: instantiate `RapidOCRBackend` or `QwenVLOCRBackend` directly.
- **Extract text from a region**:

```python
region = self.get_screenshot().crop((x1, y1, x2, y2))  # PIL crop
results = self.ocr_backend.detect_text(region)           # returns list[OcrResult]
for r in results:
    print(r.text, r.box)
```

- **CJK / special characters**: never rely on `isdigit()` or exact string match; use regex and diacritics stripping (see `games/afk_journey/mixins/guild_member_scan.py`).

## IPC & Task Execution Model

- **Most PyTauri commands live in Python, not Rust.** `__main__.py` builds its own `pytauri.Commands()` and registers `start_task`, `stop_task`, `debug`, and cache/metadata commands via `@commands.command()` / the `@tauri_profile_aware_command` wrapper. Nothing is routed through Rust.
- `start_task` spawns each task in its own `multiprocessing.Process` (`run_task`), never in-process. Logs cross the process boundary via `multiprocessing.Queue` + `QueueListener`, re-emitted as `log-message` events through PyTauri's `Emitter`.
- Task lookup: `Execute.find_command_and_execute(command, get_game_tasks())`; `get_game_tasks()` (`task_loader.py`) joins `COMMAND_REGISTRY` with `GAME_REGISTRY`.
- A task process exiting with `STATUS_ACCESS_VIOLATION` (`0xC0000005`) is auto-retried up to `_MAX_CRASH_RETRIES` (2) times — a known transient GPU/driver init race (torch/CUDA), not a bug to chase on sight.
- `task-completed` / `all-tasks-completed` events notify the frontend. `CacheGroup` (`CACHE_REGISTRY`) controls profile-aware cache invalidation to prevent races between profiles.
