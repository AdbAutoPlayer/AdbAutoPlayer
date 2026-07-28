import unittest
from unittest.mock import MagicMock, patch

from adb_auto_player.games.afk_journey.navigation import Navigation, Overview
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.template_matching.template_match_result import (
    TemplateMatchResult,
)


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


if __name__ == "__main__":
    unittest.main()
