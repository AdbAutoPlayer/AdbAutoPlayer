import unittest
from unittest.mock import patch

from pydantic import BaseModel
from pathlib import Path
from adb_auto_player.command import Command
from adb_auto_player.exceptions import NotInitializedError
from adb_auto_player.game import Game
import adb_auto_player.template_matching as template_matching


class MockGame(Game):
    def get_template_dir_path(self) -> Path:
        return Path()

    def load_config(self):
        return None

    def get_menu_commands(self) -> list[Command]:
        return list()

    def get_supported_resolutions(self) -> list[str]:
        return list()

    def get_config(self) -> BaseModel:
        return BaseModel()


class TestGame(unittest.TestCase):
    @patch.object(Game, "get_screenshot")
    def test_roi_has_changed(self, mock_get_screenshot):
        game = Game()
        with self.assertRaises(ValueError):
            game.roi_has_changed(0, 0, 0, 0)

        roi = (450, 280, 780, 400)
        f1 = Path("data") / "records_formation_1.png"
        f2 = Path("data") / "records_formation_2.png"

        game.previous_screenshot = template_matching.load_image(f1)
        mock_get_screenshot.return_value = template_matching.load_image(f1)

        # Missing scale factor
        with self.assertRaises(NotInitializedError):
            game.roi_has_changed(*roi)

        game.scale_factor = 1.0

        self.assertFalse(game.roi_has_changed(*roi))

        mock_get_screenshot.return_value = template_matching.load_image(f2)

        self.assertTrue(game.roi_has_changed(*roi))
