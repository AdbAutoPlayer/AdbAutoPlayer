from unittest.mock import MagicMock, patch

from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.games.afk_journey.custom_routine.equip_new_equipment import (
    EquipNewEquipment,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.template_matching import TemplateMatchResult

_SLEEP = "adb_auto_player.games.afk_journey.custom_routine.equip_new_equipment.sleep"


class _Stub(EquipNewEquipment):
    @property
    def settings(self):
        return MagicMock()

    @property
    def fast_timeout(self) -> float:
        return 3.0


def _match(template: str) -> TemplateMatchResult:
    return TemplateMatchResult(
        template=template,
        confidence=ConfidenceValue(1.0),
        box=Box(Point(500, 1000), 80, 40),
    )


def test_open_all_loop_is_capped():
    """Regression: the loop incremented `count` instead of `open_all_count`.

    If "Open all" stayed visible the chests were tapped forever instead of
    giving up after `max_open_all_count` (3) attempts.
    """
    bot = _Stub.__new__(_Stub)
    open_all = _match("equipment/open_all.png")
    tap = MagicMock()
    close_rewards = MagicMock()
    bot.navigate_to_resonating_hall = MagicMock()
    bot.tap = tap
    bot._close_open_all_rewards = close_rewards
    bot.wait_for_any_template = MagicMock(return_value=open_all)

    with patch(_SLEEP):
        bot._navigate_to_equipment_screen()

    # 1 tap on the Equipment button + 1 tap per "Open all" attempt.
    assert tap.call_count == 1 + 3
    assert close_rewards.call_count == 3


def test_close_rewards_taps_tap_to_close_until_gone():
    """The rewards screen is dismissed via its "Tap to close" hint."""
    bot = _Stub.__new__(_Stub)
    tap = MagicMock()
    tap_till_disappears = MagicMock()
    bot.tap = tap
    bot._tap_till_template_disappears = tap_till_disappears
    bot.wait_for_any_template = MagicMock(return_value=_match("tap_to_close.png"))

    bot._close_open_all_rewards(_match("equipment/open_all.png"))

    tap_till_disappears.assert_called_once_with("tap_to_close.png", tap_delay=2.0)
    tap.assert_not_called()


def test_close_rewards_falls_back_to_blind_tap():
    """No "Tap to close" template matched: keep the previous blind tap."""
    bot = _Stub.__new__(_Stub)
    open_all = _match("equipment/open_all.png")
    tap = MagicMock()
    bot.tap = tap
    bot.wait_for_any_template = MagicMock(side_effect=GameTimeoutError("nope"))

    with patch(_SLEEP):
        bot._close_open_all_rewards(open_all)

    tap.assert_called_once_with(open_all)
