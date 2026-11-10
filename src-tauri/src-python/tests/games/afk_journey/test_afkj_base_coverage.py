from unittest.mock import MagicMock, PropertyMock, patch

from adb_auto_player.exceptions import GameActionFailedError, GameTimeoutError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.template_matching.template_match_result import (
    TemplateMatchResult,
)


class TestAFKJourneyBaseCoverage:
    def test_start_battle_failure_coverage(self):
        """Test _start_battle failure path to cover GameActionFailedError block."""
        # Create a minimal instance of AFKJourneyBase without calling __init__
        # to avoid setup overhead
        bot = AFKJourneyBase.__new__(AFKJourneyBase)
        bot._get_settings_for_mode = MagicMock(return_value="No")
        bot.tap = MagicMock()

        # Mock wait_for_any_template to return a valid result
        match_result = TemplateMatchResult(
            template="battle/records.png",
            confidence=ConfidenceValue(1.0),
            box=Box(top_left=Point(100, 100), width=50, height=50),
        )
        bot.wait_for_any_template = MagicMock(return_value=match_result)

        # Mock _tap_coordinates_till_template_disappears to raise GameActionFailedError
        with (
            patch.object(
                AFKJourneyBase, "template_timeout", new_callable=PropertyMock
            ) as timeout,
            patch.object(
                bot,
                "_tap_coordinates_till_template_disappears",
                side_effect=GameActionFailedError("test"),
            ),
        ):
            timeout.return_value = 10.0
            # The method should return False when GameActionFailedError is caught
            assert bot._start_battle() is False

    def _run_start_battle(self, template_timeout: float) -> MagicMock:
        bot = AFKJourneyBase.__new__(AFKJourneyBase)
        bot._get_settings_for_mode = MagicMock(return_value="No")
        bot.tap = MagicMock()
        bot.sleep_action = MagicMock()
        bot.find_any_template = MagicMock(return_value=None)
        bot._click_confirm_on_popup = MagicMock(return_value=False)
        bot.wait_for_any_template = MagicMock(
            return_value=TemplateMatchResult(
                template="battle/records.png",
                confidence=ConfidenceValue(1.0),
                box=Box(top_left=Point(100, 100), width=50, height=50),
            )
        )
        tap_till = MagicMock()
        with (
            patch.object(
                AFKJourneyBase, "template_timeout", new_callable=PropertyMock
            ) as timeout,
            patch.object(bot, "_tap_coordinates_till_template_disappears", tap_till),
        ):
            timeout.return_value = template_timeout
            assert bot._start_battle() is True
        return tap_till

    def test_start_battle_tap_delay_scales_with_template_timeout(self):
        """Raising the template timeout widens the battle-start retap window."""
        kwargs = self._run_start_battle(30.0).call_args.kwargs
        assert kwargs["delay"] == 10.0
        assert kwargs["max_tap_count"] == 3

    def test_start_battle_tap_delay_has_minimum(self):
        """A tiny template timeout never goes below the 2s retap delay."""
        kwargs = self._run_start_battle(3.0).call_args.kwargs
        assert kwargs["delay"] == 2.0

    def test_find_any_excluded_hero(self):
        """Test _find_any_excluded_hero success path."""
        bot = AFKJourneyBase.__new__(AFKJourneyBase)

        match_result = TemplateMatchResult(
            template="heroes/evie.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(0, 0), 10, 10),
        )
        bot.wait_for_any_template = MagicMock(return_value=match_result)

        excluded = {"heroes/evie.png": "Evie"}
        result = bot._find_any_excluded_hero(excluded)
        assert result == "Evie"

    def test_find_any_excluded_hero_timeout(self):
        """Test _find_any_excluded_hero timeout path."""
        bot = AFKJourneyBase.__new__(AFKJourneyBase)
        bot.wait_for_any_template = MagicMock(side_effect=GameTimeoutError("timeout"))

        excluded = {"heroes/evie.png": "Evie"}
        result = bot._find_any_excluded_hero(excluded)
        assert result is None
