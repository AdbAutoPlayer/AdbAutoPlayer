"""Tests for the Union Campaign mixin's control-flow logic."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import adb_auto_player.games.afk_journey.mixins.union_campaign as union_campaign_module
import cv2
import numpy as np
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.games.afk_journey.battle_state import BattleState, Mode
from adb_auto_player.games.afk_journey.mixins.union_campaign import UnionCampaignMixin
from adb_auto_player.games.afk_journey.settings import Settings, UnionCampaignSettings
from adb_auto_player.template_matching.template_matcher import TemplateMatcher


class _Stub(UnionCampaignMixin):
    """Minimal stub - only pure-logic/control-flow methods exercised."""

    def __init__(self) -> None:
        self._settings = MagicMock()
        self.battle_state = BattleState()

    @property
    def settings(self):
        return self._settings


class TestPushUnionCampaign:
    def test_sets_mode_and_navigates(self):
        bot = _Stub()

        with (
            patch.object(bot, "start_up") as mock_start_up,
            patch.object(bot, "navigate_to_union_campaign_screen") as mock_navigate,
            patch.object(bot, "_handle_union_campaign_screen") as mock_handle,
        ):
            bot.push_union_campaign()

        mock_start_up.assert_called_once()
        mock_navigate.assert_called_once()
        mock_handle.assert_called_once()
        assert bot.battle_state.mode == Mode.UNION_CAMPAIGN


class TestHandleUnionCampaignScreen:
    def test_taps_battle_button_when_present(self):
        bot = _Stub()
        state_result = MagicMock(template="union_campaign/battle.png")

        with (
            patch.object(
                bot, "_union_campaign_resolve_state", return_value=state_result
            ),
            patch.object(bot, "_tap_till_template_disappears") as mock_tap_till,
            patch.object(bot, "_handle_battle_screen", return_value=False),
            patch("adb_auto_player.games.afk_journey.mixins.union_campaign.sleep"),
        ):
            bot._handle_union_campaign_screen()

        mock_tap_till.assert_called_once_with("union_campaign/battle.png")

    def test_no_tap_when_already_on_records_screen(self):
        bot = _Stub()
        state_result = MagicMock(template="battle/records.png")

        with (
            patch.object(
                bot, "_union_campaign_resolve_state", return_value=state_result
            ),
            patch.object(bot, "_tap_till_template_disappears") as mock_tap_till,
            patch.object(bot, "_handle_battle_screen", return_value=False),
            patch("adb_auto_player.games.afk_journey.mixins.union_campaign.sleep"),
        ):
            bot._handle_union_campaign_screen()

        mock_tap_till.assert_not_called()

    def test_defeat_stops_immediately(self):
        bot = _Stub()
        state_result = MagicMock(template="union_campaign/battle.png")

        with (
            patch.object(
                bot, "_union_campaign_resolve_state", return_value=state_result
            ),
            patch.object(bot, "_tap_till_template_disappears"),
            patch.object(
                bot, "_handle_battle_screen", return_value=False
            ) as mock_battle,
            patch.object(bot, "wait_for_any_template") as mock_wait,
            patch("adb_auto_player.games.afk_journey.mixins.union_campaign.sleep"),
        ):
            bot._handle_union_campaign_screen()

        mock_battle.assert_called_once()
        mock_wait.assert_not_called()

    def _run_post_battle(self, bot, wait_side_effect, disappear_side_effect=None):
        state_result = MagicMock(template="battle/records.png")
        mocks = {}
        with (
            patch.object(
                bot, "_union_campaign_resolve_state", return_value=state_result
            ),
            patch.object(bot, "_tap_till_template_disappears"),
            patch.object(
                bot, "_handle_battle_screen", side_effect=[True, False]
            ) as mocks["battle"],
            patch.object(
                bot, "wait_for_any_template", side_effect=wait_side_effect
            ) as mocks["wait"],
            patch.object(
                bot,
                "wait_until_template_disappears",
                side_effect=disappear_side_effect,
            ) as mocks["disappear"],
            patch.object(bot, "tap") as mocks["tap"],
            patch.object(bot, "sleep_navigation"),
            patch.object(bot, "capture_debug_screenshot") as mocks["debug"],
            patch("adb_auto_player.games.afk_journey.mixins.union_campaign.sleep"),
        ):
            bot._handle_union_campaign_screen()
        return mocks

    def test_win_loads_next_floor_and_continues(self):
        """Regression: a win must keep pushing to the next floor.

        After VICTORY > Continue the next floor's formation screen loads
        directly. Its "Records" button sits bottom-left, outside the old centre
        crop, so the post-battle wait timed out after one win.
        """
        bot = _Stub()
        records = MagicMock(template="battle/records.png")

        mocks = self._run_post_battle(bot, [records])

        assert mocks["battle"].call_count == 2
        assert (
            mocks["wait"].call_args.kwargs["crop_regions"]
            == UnionCampaignMixin._POST_BATTLE_CROP_REGIONS
        )
        mocks["tap"].assert_not_called()
        mocks["debug"].assert_not_called()

    def test_victory_still_visible_taps_continue_again(self):
        bot = _Stub()
        continue_button = MagicMock(template="arena/continue.png")
        records = MagicMock(template="battle/records.png")

        mocks = self._run_post_battle(bot, [continue_button, records])

        assert mocks["battle"].call_count == 2
        mocks["tap"].assert_called_once_with(continue_button)
        mocks["disappear"].assert_called_once()

    def test_lingering_victory_screen_is_not_treated_as_completion(self):
        """Regression: "Union Campaign completed" logged 4s after a win.

        VICTORY lingers briefly after the Continue tap, so the loop saw
        Continue again, re-tapped it 3 times in a row and gave up while the
        next floor was still loading. It now waits for Continue to disappear
        before re-checking.
        """
        bot = _Stub()
        continue_button = MagicMock(template="arena/continue.png")
        records = MagicMock(template="battle/records.png")
        # Continue stays visible for this many checks unless the code waits
        # for it to disappear.
        screen = {"continue_checks_left": 5}

        def fake_wait(*_, **__):
            if screen["continue_checks_left"] > 0:
                screen["continue_checks_left"] -= 1
                return continue_button
            return records

        def fake_wait_until_disappears(*_, **__):
            screen["continue_checks_left"] = 0

        mocks = self._run_post_battle(
            bot, fake_wait, disappear_side_effect=fake_wait_until_disappears
        )

        assert mocks["battle"].call_count == 2
        mocks["debug"].assert_not_called()

    def test_no_next_floor_stops(self):
        bot = _Stub()

        mocks = self._run_post_battle(bot, GameTimeoutError("nope"))

        mocks["battle"].assert_called_once()
        mocks["debug"].assert_called_once_with("union_campaign_no_next_floor")

    def test_continue_retries_are_capped(self):
        bot = _Stub()
        continue_button = MagicMock(template="arena/continue.png")

        mocks = self._run_post_battle(
            bot,
            [continue_button] * 10,
            disappear_side_effect=GameTimeoutError("still visible"),
        )

        mocks["battle"].assert_called_once()
        assert (
            mocks["tap"].call_count == UnionCampaignMixin._POST_BATTLE_MAX_CONTINUE_TAPS
        )

    def test_uses_union_campaign_settings_flag(self):
        bot = _Stub()
        bot.settings.union_campaign.use_suggested_formations = "sentinel-value"
        state_result = MagicMock(template="union_campaign/battle.png")

        with (
            patch.object(
                bot, "_union_campaign_resolve_state", return_value=state_result
            ),
            patch.object(bot, "_tap_till_template_disappears"),
            patch.object(
                bot, "_handle_battle_screen", return_value=False
            ) as mock_battle,
            patch("adb_auto_player.games.afk_journey.mixins.union_campaign.sleep"),
        ):
            bot._handle_union_campaign_screen()

        mock_battle.assert_called_once_with("sentinel-value")


_DATA_DIR = Path(__file__).parents[1] / "data"
_TEMPLATE_DIR = (
    Path(__file__).parents[4] / "adb_auto_player/games/afk_journey/templates"
)


def _imread(path: Path) -> np.ndarray:
    image = cv2.imread(str(path))
    assert image is not None, f"Could not read {path}"
    return image


class TestPostBattleTemplatesOnRealScreens:
    """Post-battle templates on real captures.

    The data files are the bottom strips (y >= 85%) of 1080x1920 screenshots,
    i.e. exactly the region `_POST_BATTLE_CROP_REGIONS` keeps.
    """

    def _match(self, strip: str, template: str):
        return TemplateMatcher.find_template_match(
            _imread(_DATA_DIR / strip), _imread(_TEMPLATE_DIR / template)
        )

    def test_victory_screen_shows_continue_not_records(self):
        strip = "union_campaign_victory_bottom.png"
        assert self._match(strip, UnionCampaignMixin._VICTORY_CONTINUE_TEMPLATE)
        assert self._match(strip, "battle/records.png") is None

    def test_next_floor_screen_shows_records_not_continue(self):
        strip = "union_campaign_next_floor_bottom.png"
        assert self._match(strip, "battle/records.png")
        assert self._match(strip, UnionCampaignMixin._VICTORY_CONTINUE_TEMPLATE) is None


class _TimedStub(_Stub):
    template_timeout = 10.0


class TestPostBattleWithRealWaits:
    """Regression: "Union Campaign completed" ~3.5s after a win, no tap logged.

    Uses the real `wait_for_any_template` / `wait_until_template_disappears`
    against a simulated screen on a fake clock. VICTORY lingers for a moment
    after the result handler's Continue tap, then the loading screen shows
    nothing for a few seconds before the next floor's "Records" appears. The
    default `ensure_order` re-check only waits 3s, so it timed out during
    loading and the campaign was reported as completed.
    """

    _VICTORY_UNTIL = 0.3
    _NEXT_FLOOR_AT = 5.0

    def test_loading_screen_after_victory_continues_to_next_floor(self):
        bot = _TimedStub()
        bot.default_threshold = MagicMock()
        continue_button = MagicMock(template="arena/continue.png")
        records = MagicMock(template="battle/records.png")
        clock = {"now": 0.0}

        def fake_sleep(seconds):
            clock["now"] += seconds

        def visible():
            if clock["now"] < self._VICTORY_UNTIL:
                return continue_button
            if clock["now"] >= self._NEXT_FLOOR_AT:
                return records
            return None  # loading screen

        def fake_find_any_template(templates, **_):
            match = visible()
            return match if match and match.template in templates else None

        def fake_find_template_match(template, **_):
            match = visible()
            return match if match and match.template == template else None

        state_result = MagicMock(template="battle/records.png")
        template_mixin = "adb_auto_player.game._template_mixin"
        with (
            patch(f"{template_mixin}.sleep", side_effect=fake_sleep),
            patch(f"{template_mixin}.monotonic", side_effect=lambda: clock["now"]),
            patch.object(
                bot, "_union_campaign_resolve_state", return_value=state_result
            ),
            patch.object(
                bot, "_handle_battle_screen", side_effect=[True, False]
            ) as mock_battle,
            patch.object(bot, "find_any_template", side_effect=fake_find_any_template),
            patch.object(
                bot, "game_find_template_match", side_effect=fake_find_template_match
            ),
            patch.object(bot, "tap"),
            patch.object(bot, "capture_debug_screenshot") as mock_debug,
        ):
            bot._handle_union_campaign_screen()

        assert mock_battle.call_count == 2
        mock_debug.assert_not_called()


class TestUnionCampaignSettings:
    """Union Campaign has no paid attempts, so "Spend Gold" must not show up."""

    def test_spend_gold_hidden_from_ui_schema(self):
        schema = Settings.model_json_schema(by_alias=True)
        properties = schema["$defs"]["UnionCampaignSettings"]["properties"]
        assert "Spend Gold" not in properties
        assert "Attempts" in properties

    def test_spend_gold_always_false_and_not_saved(self):
        settings = UnionCampaignSettings.model_validate({"Spend Gold": True})
        assert settings.spend_gold is False
        assert "Spend Gold" not in settings.model_dump(by_alias=True)


class TestSweepIsNeverAutomated:
    """Regression/safety test.

    Sweep is a limited daily resource the user manages manually. The mixin
    must never reference a Sweep template or tap target - prose mentioning
    "Sweep" in comments/docstrings (explaining why it's excluded) is fine.
    """

    def test_no_sweep_template_or_tap_target(self):
        source = Path(union_campaign_module.__file__).read_text(encoding="utf-8")

        assert re.search(r"sweep.{0,30}\.png|\.png.{0,30}sweep", source, re.I) is None
