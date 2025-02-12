import unittest
from unittest.mock import patch, MagicMock

import adb_auto_player.main


class TestMain(unittest.TestCase):
    @patch("builtins.print")
    def test_get_gui_games_menu(self, mock_print: MagicMock):
        menu_json_string = adb_auto_player.main.get_gui_games_menu()
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
