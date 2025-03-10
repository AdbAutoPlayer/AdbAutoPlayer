"""Infinity Nikki Main Module."""

from enum import StrEnum

from adb_auto_player.command import Command
from adb_auto_player.games.infinity_nikki.config import Config
from adb_auto_player.games.infinity_nikki.mixins.sheep_minigame import (
    SheepMinigameMixin,
)
from adb_auto_player.ipc.game_gui import GameGUIOptions, MenuOption


class _Category(StrEnum):
    MINIGAMES = "Minigames"


class InfinityNikki(
    SheepMinigameMixin,
):
    """Infinity Nikki Game."""

    def get_cli_menu_commands(self) -> list[Command]:
        """Get CLI menu commands."""
        return [
            Command(
                name="SheepMinigame",
                action=self.afk_sheep_minigame,
                kwargs={},
                menu_option=MenuOption(
                    label="Sheep Minigame",
                    category=_Category.MINIGAMES,
                    tooltip='This runs the Sheep Minigame till "Runs" count or '
                    "Bling cap is reached.",
                ),
            ),
        ]

    def get_gui_options(self) -> GameGUIOptions:
        """Get the GUI options from TOML."""
        return GameGUIOptions(
            game_title="Infinity Nikki",
            config_path="infinity_nikki/InfinityNikki.toml",
            menu_options=self._get_menu_options_from_cli_menu(),
            categories=[_Category.MINIGAMES],
            constraints=Config.get_constraints(),
        )
