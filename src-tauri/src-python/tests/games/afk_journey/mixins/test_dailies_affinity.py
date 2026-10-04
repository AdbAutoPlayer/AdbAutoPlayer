from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from adb_auto_player.games.afk_journey.mixins.dailies import DailiesMixin

_MODULE = "adb_auto_player.games.afk_journey.mixins.dailies"


class _Stub(DailiesMixin):
    """Minimal stub — device, navigation and template matching are mocked."""

    def __init__(self):
        self.get_screenshot = MagicMock(
            return_value=np.zeros((1920, 1080, 3), dtype=np.uint8)
        )
        # Typed MagicMock handles for assertions: the overridden attributes
        # keep the method signatures in the type checker's view
        self.template_mock = MagicMock(return_value=None)
        self.tap_mock = MagicMock()
        self.navigate_mock = MagicMock()
        self.capture_mock = MagicMock()
        self.back_mock = MagicMock()
        self.click_hero_mock = MagicMock()
        self.game_find_template_match = self.template_mock
        self.tap = self.tap_mock
        self.navigate_to_world = self.navigate_mock
        self.capture_debug_screenshot = self.capture_mock
        self.press_back_button = self.back_mock
        self._click_hero = self.click_hero_mock


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(f"{_MODULE}.sleep", lambda _: None)


def _scanner(names: list[str], hero_list_size: int = 3) -> MagicMock:
    scanner = MagicMock()
    scanner.load_hero_names.return_value = True
    scanner.canonical_hero_names = [f"hero{i}" for i in range(hero_list_size)]
    scanner.read_hero_name.side_effect = names
    return scanner


def _run(bot: _Stub, scanner: MagicMock) -> None:
    with patch(f"{_MODULE}.HeroScanner", return_value=scanner):
        bot.raise_hero_affinity()


class TestRaiseHeroAffinity:
    def test_clicks_every_hero_through_chippy(self):
        bot = _Stub()
        _run(bot, _scanner(["Odie", "Rowan", "Chippy"]))

        assert bot.click_hero_mock.call_count == 3
        bot.capture_mock.assert_not_called()

    def test_stops_without_clicking_when_back_does_not_recover(self):
        # Shop popup instead of a hero: both reads before and after back fail
        bot = _Stub()
        _run(bot, _scanner(["Odie"] + ["Unknown"] * 4))

        assert bot.click_hero_mock.call_count == 1
        bot.back_mock.assert_called_once()
        bot.capture_mock.assert_called_once_with("affinity_not_on_hero_screen")
        bot.navigate_mock.assert_called()

    def test_back_closes_popup_and_affinity_continues(self):
        bot = _Stub()
        _run(bot, _scanner(["Odie", "Unknown", "Unknown", "Rowan", "Chippy"]))

        assert bot.click_hero_mock.call_count == 3
        bot.back_mock.assert_called_once()

    def test_slow_transition_is_retried(self):
        bot = _Stub()
        _run(bot, _scanner(["Unknown", "Odie", "Chippy"]))

        assert bot.click_hero_mock.call_count == 2
        bot.capture_mock.assert_not_called()

    def test_loop_is_capped_when_chippy_never_appears(self):
        bot = _Stub()
        scanner = _scanner([], hero_list_size=2)
        scanner.read_hero_name.side_effect = None
        scanner.read_hero_name.return_value = "Odie"
        _run(bot, scanner)

        assert bot.click_hero_mock.call_count == 2 + 20
        bot.capture_mock.assert_called_once_with("affinity_limit_reached")

    def test_skipped_when_hero_list_unavailable(self):
        bot = _Stub()
        scanner = _scanner([])
        scanner.load_hero_names.return_value = False
        _run(bot, scanner)

        bot.tap_mock.assert_not_called()
        bot.click_hero_mock.assert_not_called()
