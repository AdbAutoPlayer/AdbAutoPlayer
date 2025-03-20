"""Avatar Realms Collide Main Module."""

import logging
from enum import StrEnum
from time import sleep

from adb_auto_player import Coordinates, CropRegions, GameTimeoutError
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
            self._click_help()
            self._alliance_research_and_gift()
            # train troops
            # gathering
            # auto build
            # auto research
            sleep(5)

    def _alliance_research_and_gift(self) -> None:
        if not self.game_find_template_match("gui/map.png"):
            logging.warning("Map not found skipping alliance research and gift.")
            return
        self.click(Coordinates(1560, 970))
        self.wait_for_template("alliance/alliance_shop.png")
        sleep(0.5)
        research = self.game_find_template_match("alliance/research.png")
        if research:
            self.click(Coordinates(*research))
            self._handle_alliance_research()
        gift = self.game_find_template_match("alliance/gift.png")
        if gift:
            self.click(Coordinates(*gift))
            sleep(2)
            self._handle_alliance_gift()
        self.press_back_button()
        sleep(0.5)

    def _handle_alliance_gift(self) -> None:
        treasure_chest = self.game_find_template_match("alliance/treasure_chest.png")
        if treasure_chest:
            self.click(Coordinates(*treasure_chest))
            sleep(0.5)
            ok = self.game_find_template_match("gui/ok.png")
            if ok:
                self.click(Coordinates(*ok))
                sleep(0.5)
        claim_all = self.game_find_template_match("alliance/claim_all.png")
        if claim_all:
            self.click(Coordinates(*claim_all))
            sleep(2)
        gift_chest = self.game_find_template_match("alliance/gift_chest.png")
        if not gift_chest:
            return
        self.click(Coordinates(*gift_chest))
        sleep(0.5)
        while claim := self.game_find_template_match("alliance/claim.png"):
            self.click(Coordinates(*claim))
            sleep(0.5)
            refresh = self.game_find_template_match("alliance/gift_chest_refresh.png")
            if refresh:
                self.click(Coordinates(*refresh))
                sleep(0.5)
        self.press_back_button()
        sleep(0.5)
        return

    def _handle_alliance_research(self) -> None:
        try:
            self.wait_for_template(
                "alliance/research_development.png",
                timeout=5,
            )
        except GameTimeoutError:
            logging.warning("Alliance Research window not found.")
            return None
        recommended = self.game_find_template_match("alliance/research_recommended.png")
        if not recommended:
            self.game_find_template_match("alliance/research_territory.png")
            recommended = self.game_find_template_match(
                "alliance/research_recommended.png"
            )

        if not recommended:
            self.game_find_template_match("alliance/research_warfare.png")
            recommended = self.game_find_template_match(
                "alliance/research_recommended.png"
            )

        if not recommended:
            logging.warning("No recommended alliance research.")
            return
        x, y = recommended
        self.click(Coordinates(x + 80, y - 150))
        sleep(2)
        donate = self.game_find_template_match(
            "alliance/research_donate.png", crop=CropRegions(left=0.6, top=0.6)
        )

        if donate:
            for i in range(20):
                self.click(Coordinates(*donate))
                sleep(0.1)
        x_button = self.game_find_template_match("gui/x.png")
        if x_button:
            self.click(Coordinates(*x_button))
            sleep(0.5)
        self.press_back_button()
        sleep(0.5)
        return

    def _click_resources(self) -> None:
        logging.info("Clicking resources")
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

    def _click_help(self) -> None:
        logging.info("Clicking help")
        while result := self.find_any_template(
            [
                "alliance/help_bubble.png",
                "alliance/help_button.png",
            ],
            threshold=0.7,
            crop=CropRegions(top=0.1, right=0.1),
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
