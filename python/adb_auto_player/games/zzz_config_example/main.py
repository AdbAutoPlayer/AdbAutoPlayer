"""Play Store Main Module."""

import logging

from adb_auto_player import Command, Game
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.decorators.register_custom_routine_choice import (
    register_custom_routine_choice,
)
from adb_auto_player.games.zzz_config_example.config import Config
from adb_auto_player.ipc import GameGUIOptions
from pydantic import BaseModel


class PlayStore(Game):
    """Just for GUI testing."""

    def __init__(self) -> None:
        """Initialize PlayStore."""
        super().__init__()
        self.package_name_substrings = [
            "com.android.vending",
        ]

    @register_command(
        gui=GuiMetadata(label="Label", category="Category", tooltip="Tooltip")
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

    def get_gui_options(self) -> GameGUIOptions:
        """Get the GUI options from TOML."""
        return GameGUIOptions(
            game_title="Dev Config Testing",
            config_path="zzz_config_example/ZzzConfigExample.toml",
            menu_options=self._get_menu_options_from_cli_menu(),
            categories=[],
            constraints=Config.get_constraints(),
        )

    def get_cli_menu_commands(self) -> list[Command]:
        """Get the CLI menu commands."""
        return []

    def _load_config(self):
        raise NotImplementedError()
