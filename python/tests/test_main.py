"""Pytest Main Module."""

import unittest
from unittest.mock import MagicMock, patch

from adb_auto_player.commands.gui_menu import get_gui_games_menu


class TestMain(unittest.TestCase):
    """Test Main Module."""

    @patch("builtins.print")
    def test_get_gui_games_menu(self, mock_print: MagicMock) -> None:
        """Test get_gui_games_menu function.

        This test verifies that the get_gui_games_menu function returns a JSON string
        containing the expected game menu details for the GUI. It checks that the
        JSON string includes the game title, config path, menu options, and specific
        constraints. It also ensures that the print function is not called, indicating
        no output to the console during the function's execution.
        """
        menu_json_string = get_gui_games_menu()
        self.assertIn('"game_title": "AFK Journey"', menu_json_string)
        self.assertIn(
            '"config_path": "afk_journey/AFKJourney.toml"',
            menu_json_string,
        )
        # check Menu Buttons are sent
        self.assertIn("AFK Stages", menu_json_string)
        # check Constraints are sent
        self.assertIn("Elijah & Lailah", menu_json_string)
        self.assertIn("Granny Dahnie", menu_json_string)
        self.assertIn("Cecia", menu_json_string)
        self.assertIn('"maximum": 7,', menu_json_string)
        # check print is called for ipc
        mock_print.assert_not_called()
