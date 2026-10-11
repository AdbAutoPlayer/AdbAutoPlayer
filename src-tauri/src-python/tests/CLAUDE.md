# Python Tests

Run from `src-tauri/`. No device or Tauri window is required.

```bash
uv run pytest tests/games/afk_journey/mixins/test_guild_member_scan.py::TestCanonicalizeObservations::test_ranked_observation_wins_over_null_supplements -v
```

Key files: `test_game.py`, `test_e2e_flow.py`, `games/afk_journey/mixins/test_guild_member_scan.py`, `ocr/`, `template_matching/`, `utils/dummy_game.py` (minimal `Game` stub).

## Mock Pattern for pytauri / ext_mod

Only needed if the module under test imports `pytauri` or `adb_auto_player.ext_mod` (directly or transitively). Most pure-logic mixin tests don't need it.

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

## Minimal Stub for Mixin Tests

```python
from adb_auto_player.games.afk_journey.mixins.my_mixin import MyMixin

class _Stub(MyMixin):
    """Minimal stub — only pure-logic methods exercised."""

def test_something():
    bot = _Stub()
    result = bot._some_pure_method(...)
    assert result == expected
```

## Tests That Need Real Images

```python
from pathlib import Path
TEST_DATA_DIR = Path(__file__).parent / "data"  # put PNGs here
```
