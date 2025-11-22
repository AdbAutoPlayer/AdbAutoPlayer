"""Play Store Main Module."""

import logging
import pprint

from adb_auto_player.decorators import (
    register_command,
    register_custom_routine_choice,
    register_game,
)
from adb_auto_player.game import Game
from adb_auto_player.games.zzz_config_example.settings import Settings
from adb_auto_player.models.decorators import GameGUIMetadata, GUIMetadata
from pydantic import BaseModel


@register_game(
    name="Google Play",
    settings_file="ZzzConfigExample.toml",
    gui_metadata=GameGUIMetadata(settings_class=Settings),
)
class PlayStore(Game):
    """Just for GUI testing."""

    @property
    def settings(self) -> BaseModel:
        return BaseModel()

    def __init__(self) -> None:
        """Initialize PlayStore."""
        super().__init__()
        self.package_name_prefixes = [
            "com.android.vending",
        ]

    @register_command(
        gui=GUIMetadata(label="Log Settings", category="Category", tooltip="Tooltip")
    )
    def _test_gui(self) -> None:
        logging.info(f"{pprint.pformat(self.settings)}")

    @register_command()
    def _test_cli(self) -> None:
        logging.info("CLI")

    @register_custom_routine_choice(label="Choice")
    def _test_custom_routine(self) -> None:
        logging.info("CUSTOM ROUTINE")

    def get_settings(self) -> BaseModel:
        return Settings.from_toml(self.settings_file_path)
