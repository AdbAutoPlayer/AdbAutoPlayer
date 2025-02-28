from adb_auto_player.command import Command
from adb_auto_player.games.infinity_nikki.mixins.sheep_minigame import (
    SheepMinigameMixin,
)
from adb_auto_player.ipc.game_gui import GameGUIOptions


class InfinityNikki(
    SheepMinigameMixin,
):
    def get_cli_menu_commands(self) -> list[Command]:
        return [
            Command(
                name="SheepMinigame",
                gui_label="Sheep Minigame",
                action=self.afk_sheep_minigame,
                kwargs={},
            ),
        ]

    def get_gui_options(self) -> GameGUIOptions:
        return GameGUIOptions(
            game_title="Infinity Nikki",
            config_path="infinity_nikki/InfinityNikki.toml",
            menu_options=self._get_menu_options_from_cli_menu(),
            constraints={},
        )
