"""Infinity Nikki Main Module."""

from adb_auto_player.command import Command
from adb_auto_player.games.infinity_nikki.config import Config
from adb_auto_player.games.infinity_nikki.mixins.sheep_minigame import (
    SheepMinigameMixin,
)
from adb_auto_player.ipc.game_gui import GameGUIOptions


class InfinityNikki(
    SheepMinigameMixin,
):
    """Infinity Nikki Game."""

    def get_cli_menu_commands(self) -> list[Command]:
        """Get CLI menu commands."""
        return [
            Command(
                name="SheepMinigame",
                gui_label="Sheep Minigame",
                action=self.afk_sheep_minigame,
                kwargs={},
            ),
        ]

    def get_gui_options(self) -> GameGUIOptions:
        """Get the GUI options from TOML."""
        return GameGUIOptions(
            game_title="Infinity Nikki",
            config_path="infinity_nikki/InfinityNikki.toml",
            menu_options=self._get_menu_options_from_cli_menu(),
            constraints=Config.get_constraints(),
        )
