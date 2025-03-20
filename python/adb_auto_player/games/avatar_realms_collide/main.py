"""Avatar Realms Collide Main Module."""

from enum import StrEnum
from time import sleep

from adb_auto_player import Coordinates, CropRegions
from adb_auto_player.command import Command
from adb_auto_player.games.avatar_realms_collide.base import AvatarRealmsCollideBase
from adb_auto_player.games.avatar_realms_collide.config import Config
from adb_auto_player.ipc.game_gui import GameGUIOptions, MenuOption


class ModeCategory(StrEnum):
    """Enumeration for mode categories used in the GUIs accordion menu."""

    ALL = "All"


class AvatarRealmsCollide(AvatarRealmsCollideBase):
    """Avatar Realms Collide Game."""

    def auto_play(self) -> None:
        """WIP."""
        self.start_up(device_streaming=True)
        while True:
            self._click_resources()
            sleep(5)

    def _click_resources(self) -> None:
        while result := self.find_any_template(
            [
                "harvest/food.png",
                "harvest/wood.png",
                "harvest/stone.png",
                "harvest/gold.png",
            ],
            threshold=0.7,
            crop=CropRegions(top=0.1),
        ):
            _, x, y = result
            self.click(Coordinates(x, y))
            sleep(1)

    def get_cli_menu_commands(self) -> list[Command]:
        """Get CLI menu commands."""
        return [
            Command(
                name="AvatarRealmsCollideAutoPlay",
                action=self.auto_play,
                kwargs={},
                menu_option=MenuOption(
                    label="Auto Play",
                    category=ModeCategory.ALL,
                ),
            ),
        ]

    def get_gui_options(self) -> GameGUIOptions:
        """Get the GUI options from TOML."""
        return GameGUIOptions(
            game_title="Avatar Realms Collide",
            config_path="avatar_realms_collide/AvatarRealmsCollide.toml",
            menu_options=self._get_menu_options_from_cli_menu(),
            categories=[ModeCategory.ALL],
            constraints=Config.get_constraints(),
        )
