import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import cv2
import numpy as np
from adb_auto_player.exceptions import AutoPlayerWarningError
from adb_auto_player.games.afk_journey.navigation import Navigation, Overview
from adb_auto_player.image_manipulation import Cropping
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.template_matching.template_match_result import (
    TemplateMatchResult,
)
from adb_auto_player.template_matching.template_matcher import TemplateMatcher


class MockNavigation(Navigation):
    @property
    def settings(self):
        return MagicMock()


class TestNavigationExtended(unittest.TestCase):
    """Extended tests for Navigation class coverage."""

    def setUp(self):
        # Create a concrete instance. Mocks are kept as their own properly-typed
        # attributes (self.mock_*) rather than read back through self.nav.* —
        # the type checker still sees self.nav.tap etc. as the real bound method
        # from Navigation/_InputMixin, not as a MagicMock, once assigned.
        self.nav = MockNavigation.__new__(MockNavigation)
        self.mock_find_any_template = MagicMock()
        self.mock_handle_popup_messages = MagicMock()
        self.mock_press_back_button = MagicMock()
        self.mock_tap = MagicMock()
        self.nav.find_any_template = self.mock_find_any_template
        self.nav.handle_popup_messages = self.mock_handle_popup_messages
        self.nav.press_back_button = self.mock_press_back_button
        self.nav.tap = self.mock_tap
        self.nav.CENTER_POINT = Point(540, 960)

    def test_handle_overview_navigation_world(self):
        """Test recognition of world template."""
        match = TemplateMatchResult(
            template="navigation/time_of_day.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(0, 0), 10, 10),
        )
        self.mock_find_any_template.return_value = match

        result = self.nav._handle_overview_navigation(Overview.WORLD)
        self.assertEqual(result, Overview.WORLD)

    def test_handle_overview_navigation_homestead_enter(self):
        """Test homestead enter template."""
        match = TemplateMatchResult(
            template="navigation/homestead/homestead_enter.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(100, 100), 50, 50),
        )
        self.mock_find_any_template.return_value = match

        # When we find homestead_enter but want homestead, it should return None
        # as it needs to enter homestead via tap first.
        result = self.nav._handle_overview_navigation(Overview.HOMESTEAD)
        self.assertIsNone(result)
        self.mock_tap.assert_called_once()

    def test_handle_overview_navigation_homestead_world(self):
        """Test homestead world template (entering homestead from world)."""
        match = TemplateMatchResult(
            template="navigation/homestead/world.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(100, 100), 50, 50),
        )
        self.mock_find_any_template.return_value = match

        result = self.nav._handle_overview_navigation(Overview.HOMESTEAD)
        self.assertEqual(result, Overview.HOMESTEAD)

    def test_handle_overview_navigation_notice(self):
        """Test notice template (game entry)."""
        match = TemplateMatchResult(
            template="navigation/notice.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(100, 100), 50, 50),
        )
        self.mock_find_any_template.return_value = match

        result = self.nav._handle_overview_navigation(Overview.WORLD)
        self.assertIsNone(result)
        self.mock_tap.assert_called_once_with(self.nav.CENTER_POINT)

    def test_handle_overview_navigation_confirm(self):
        """Test confirm template."""
        match = TemplateMatchResult(
            template="navigation/confirm.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(100, 100), 50, 50),
        )
        self.mock_find_any_template.return_value = match
        self.mock_handle_popup_messages.return_value = False

        result = self.nav._handle_overview_navigation(Overview.WORLD)
        self.assertIsNone(result)
        self.mock_tap.assert_called_once_with(match)

    def test_handle_overview_navigation_dotdotdot(self):
        """Test dotdotdot template."""
        match = TemplateMatchResult(
            template="navigation/dotdotdot.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(100, 100), 50, 50),
        )
        self.mock_find_any_template.return_value = match

        result = self.nav._handle_overview_navigation(Overview.WORLD)
        self.assertIsNone(result)
        self.mock_press_back_button.assert_called_once()

    def test_handle_overview_navigation_popup_handling(self):
        """Test that popup handling prevents hitting Back button."""
        self.mock_find_any_template.return_value = None
        self.mock_handle_popup_messages.return_value = True

        with patch("time.sleep", return_value=None):
            result = self.nav._handle_overview_navigation(Overview.WORLD)
            self.assertIsNone(result)
            self.mock_handle_popup_messages.assert_called_once()

    def test_handle_overview_navigation_back_button_fallback(self):
        """Test that Back button is hit if no template and no popup."""
        self.mock_find_any_template.return_value = None
        self.mock_handle_popup_messages.return_value = False

        with patch("time.sleep", return_value=None):
            result = self.nav._handle_overview_navigation(Overview.WORLD)
            self.assertIsNone(result)
            self.mock_press_back_button.assert_called_once()

    def test_handle_overview_navigation_arcane_labyrinth(self):
        """Test arcane labyrinth crest selection."""
        match = TemplateMatchResult(
            template="arcane_labyrinth/select_a_crest.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(100, 100), 50, 50),
        )
        self.mock_find_any_template.return_value = match

        result = self.nav._handle_overview_navigation(Overview.WORLD)
        self.assertIsNone(result)
        # Should call tap twice (crest and confirm/result)
        self.assertEqual(self.mock_tap.call_count, 2)

    def test_handle_overview_navigation_homestead_world_entering(self):
        """Test homestead world template when we want world."""
        match = TemplateMatchResult(
            template="navigation/homestead/world.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(100, 100), 50, 50),
        )
        self.mock_find_any_template.return_value = match

        # If we want WORLD but are looking at the 'world' button in homestead
        result = self.nav._handle_overview_navigation(Overview.WORLD)
        self.assertIsNone(result)
        self.mock_tap.assert_called_once_with(match)

    def test_handle_overview_navigation_homestead_enter_world(self):
        """Test homestead enter template when we want world."""
        match = TemplateMatchResult(
            template="navigation/homestead/homestead_enter.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(100, 100), 50, 50),
        )
        self.mock_find_any_template.return_value = match

        # If we want WORLD and find homestead_enter, it means we are in WORLD
        result = self.nav._handle_overview_navigation(Overview.WORLD)
        self.assertEqual(result, Overview.WORLD)


class TestFindInBattleModes(unittest.TestCase):
    """Regression tests for the Battle Modes scroll-and-find loop.

    A single long/fast swipe could fling past the target entry on real
    phone touchscreens (vs. emulators), leaving the entry off-screen and
    the search timing out. `_find_in_battle_modes` now retries a shorter
    swipe, re-checking for the template after each one instead of
    swiping once and hoping.
    """

    def setUp(self):
        self.nav = MockNavigation.__new__(MockNavigation)
        self.mock_game_find_template_match = MagicMock()
        self.mock_swipe_up = MagicMock()
        self.mock_sleep_navigation = MagicMock()
        self.mock_wait_for_template = MagicMock()
        self.nav.game_find_template_match = self.mock_game_find_template_match
        self.nav.swipe_up = self.mock_swipe_up
        self.nav.sleep_navigation = self.mock_sleep_navigation
        self.nav.wait_for_template = self.mock_wait_for_template

    def test_stops_swiping_once_template_is_found(self):
        """Swiping should stop as soon as the entry becomes visible."""
        match = TemplateMatchResult(
            template="battle_modes/duras_trials.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(100, 100), 50, 50),
        )
        self.mock_game_find_template_match.side_effect = [None, None, match]
        self.mock_wait_for_template.return_value = match

        result = self.nav._find_in_battle_modes(
            template="battle_modes/duras_trials.png",
            timeout_message="not found",
        )

        self.assertEqual(result, match)
        self.assertEqual(self.mock_swipe_up.call_count, 2)
        self.assertEqual(self.mock_sleep_navigation.call_count, 2)

    def test_gives_up_swiping_after_max_attempts(self):
        """Should not swipe forever if the entry never appears."""
        self.mock_game_find_template_match.return_value = None
        self.mock_wait_for_template.return_value = MagicMock()

        self.nav._find_in_battle_modes(
            template="battle_modes/duras_trials.png",
            timeout_message="not found",
        )

        self.assertEqual(
            self.mock_swipe_up.call_count,
            self.nav._BATTLE_MODES_SWIPE_MAX_ATTEMPTS,
        )

    def test_no_swipe_when_already_visible(self):
        """Should not swipe at all if the entry is already on screen."""
        match = TemplateMatchResult(
            template="battle_modes/duras_trials.png",
            confidence=ConfidenceValue(1.0),
            box=Box(Point(100, 100), 50, 50),
        )
        self.mock_game_find_template_match.return_value = match
        self.mock_wait_for_template.return_value = match

        self.nav._find_in_battle_modes(
            template="battle_modes/duras_trials.png",
            timeout_message="not found",
        )

        self.mock_swipe_up.assert_not_called()


def _match(template: str, y: int) -> TemplateMatchResult:
    return TemplateMatchResult(
        template=template,
        confidence=ConfidenceValue(1.0),
        box=Box(Point(30, y), 260, 50),
    )


class TestDurasTrialsComingSoon(unittest.TestCase):
    """Regression: locked Dura's Trials sits under the "Coming Soon" header.

    Its label is identical to the unlocked one, so tapping it did nothing and
    `_tap_till_template_disappears` raised GameActionFailedError, aborting
    the whole Dailies run.
    """

    def setUp(self):
        self.nav = MockNavigation.__new__(MockNavigation)
        self.mock_game_find_template_match = MagicMock()
        self.mock_find_in_battle_modes = MagicMock()
        self.mock_tap_till_disappears = MagicMock()
        self.nav.game_find_template_match = self.mock_game_find_template_match
        self.nav.navigate_to_battle_modes_screen = MagicMock()
        self.nav._find_in_battle_modes = self.mock_find_in_battle_modes
        self.nav._tap_till_template_disappears = self.mock_tap_till_disappears
        self.nav.sleep_action = MagicMock()
        self.nav.tap = MagicMock()
        self.nav.wait_for_template = MagicMock()

    def test_entry_below_header_is_locked(self):
        self.assertTrue(
            Navigation._is_in_coming_soon_section(
                _match("battle_modes/duras_trials.png", 1420),
                _match("battle_modes/coming_soon.png", 988),
            )
        )

    def test_entry_above_header_is_unlocked(self):
        self.assertFalse(
            Navigation._is_in_coming_soon_section(
                _match("battle_modes/duras_trials.png", 800),
                _match("battle_modes/coming_soon.png", 988),
            )
        )

    def test_no_header_is_unlocked(self):
        self.assertFalse(
            Navigation._is_in_coming_soon_section(
                _match("battle_modes/duras_trials.png", 1420), None
            )
        )

    def test_navigate_raises_warning_when_locked(self):
        dura = _match("battle_modes/duras_trials.png", 1420)
        header = _match("battle_modes/coming_soon.png", 988)
        # stop_condition (not on Dura screen) -> None, then the header lookup.
        self.mock_game_find_template_match.side_effect = [None, header]
        self.mock_find_in_battle_modes.return_value = dura

        with self.assertRaises(AutoPlayerWarningError):
            self.nav.navigate_to_duras_trials_screen()

        self.mock_tap_till_disappears.assert_not_called()

    def test_navigate_taps_when_unlocked(self):
        dura = _match("battle_modes/duras_trials.png", 1420)
        self.mock_game_find_template_match.side_effect = [None, None]
        self.mock_find_in_battle_modes.return_value = dura

        self.nav.navigate_to_duras_trials_screen()

        self.mock_tap_till_disappears.assert_called_once_with(dura.template)


_DATA_DIR = Path(__file__).parent / "data"
_TEMPLATE_DIR = (
    Path(__file__).parents[3] / "adb_auto_player/games/afk_journey/templates"
)


def _imread(path: Path) -> np.ndarray:
    image = cv2.imread(str(path))
    assert image is not None, f"Could not read {path}"
    return image


class TestIsInOverviewNight(unittest.TestCase):
    """Regression: `_is_in_overview` returned False in the World at night.

    Its crop kept only the top-right quadrant, but homestead_enter moved to the
    bottom-right and time_of_day does not match the night-only moon icon.
    `navigate_to_resonating_hall` then never tapped the Resonating Hall button
    and timed out 3 times (seen after "Opening Equipment Chests").
    """

    def setUp(self):
        self.screenshot = _imread(_DATA_DIR / "world_overview_night.png")
        self.nav = MockNavigation.__new__(MockNavigation)
        self.nav.find_any_template = MagicMock(side_effect=self._find_any_template)

    def _find_any_template(self, templates, crop_regions, **_):
        cropped = Cropping.crop(self.screenshot, crop_regions)
        for template in templates:
            if TemplateMatcher.find_template_match(
                cropped.image, _imread(_TEMPLATE_DIR / template)
            ):
                return template
        return None

    def test_world_at_night_is_overview(self):
        self.assertTrue(self.nav._is_in_overview())


if __name__ == "__main__":
    unittest.main()
