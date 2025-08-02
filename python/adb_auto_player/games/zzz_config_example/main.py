"""Play Store Main Module."""

import logging

from adb_auto_player.decorators import (
    register_command,
    register_custom_routine_choice,
    register_game,
)
from adb_auto_player.game import Game
from adb_auto_player.games.zzz_config_example.config import Config
from adb_auto_player.models.decorators import GameGUIMetadata, GUIMetadata
from pydantic import BaseModel


@register_game(
    name="Google Play",
    config_file_path="zzz_config_example/ZzzConfigExample.toml",
    gui_metadata=GameGUIMetadata(config_class=Config),
)
class PlayStore(Game):
    """Just for GUI testing."""

    def __init__(self) -> None:
        """Initialize PlayStore."""
        super().__init__()
        self.package_name_substrings = [
            "com.android.vending",
        ]

    @register_command(
        gui=GUIMetadata(label="Label", category="Category", tooltip="Tooltip")
    )
    def _test_gui(self) -> None:
        logging.info("GUI")

    @register_command()
    def _test_cli(self) -> None:
        logging.info("CLI")

    @register_custom_routine_choice(label="Choice")
    def _test_custom_routine(self) -> None:
        logging.info("CUSTOM ROUTINE")

    def get_config(self) -> BaseModel:
        """Not Implemented."""
        raise NotImplementedError()

    def _load_config(self):
        raise NotImplementedError()
