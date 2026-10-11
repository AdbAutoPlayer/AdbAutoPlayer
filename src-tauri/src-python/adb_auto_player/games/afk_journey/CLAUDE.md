# AFK Journey

## Layout

- `base.py` — `AFKJourneyBase`, composes the feature mixins.
- `settings.py` — Pydantic settings (template: `src-tauri/settings/AFKJourney.toml`).
- `navigation.py` — screen navigation helpers.
- `mixins/` — one file per feature; `guild_member_scan.py` is the most complex module in the repo.
- `custom_routine/` — custom routines.

## Add a Command

- Open or create the relevant mixin in `mixins/<feature>.py` and add the method with decorators:

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

- Add the mixin to `AFKJourneyBase` in `base.py` (follow the existing pattern).
- No frontend changes needed — the decorator wires everything automatically.

## GuildManagerScan (`mixins/guild_member_scan.py`)

- **Chest contribution OCR**: values appear as `￥8` or `个8` (icon + number), not plain `8`. Use `re.compile(r"^\D{0,3}(\d+)$")`, never `isdigit()`.
- **Rank badge vs member name**: rank badges are at x≈105, member names at x≈330+. Filter by `box.center.x < _X_CHEST_RANK_BADGE_MAX (200)` so a member named "67" is not read as a rank.
- **Scroll parameters matter**: swipe `sy=1400, ey=1100, duration=1.5` with 2.0s post-swipe sleep. Longer swipes skip entries due to inertia.
- **OCR models**: activeness + chest use RapidOCR PP-OCRv5; DR/SA rankings use Qwen2-VL-2B (≥6GB VRAM) with RapidOCR fallback.
- **CJK / Korean names** (e.g. `이른봄날`, `典明`, `旅人`): RapidOCR may output heuristic variants like `弓号言l0` → `이른봄날`; diacritics stripping is applied to both OCR output and the member name before comparison.
- Guild member list comes from the Supabase API; keep `GUILD_MEMBERS` in test scripts updated when membership changes.
- To debug missing entries, use the `debug-guild-scan` skill.
