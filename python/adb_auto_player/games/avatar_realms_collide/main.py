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

    gather_count: int = 0

    def auto_play(self) -> None:
        """WIP."""
        self.start_up(device_streaming=True)
        while True:
            search = self.game_find_template_match(
                "gathering/search.png",
                crop=CropRegions(right=0.8, top=0.6),
            )
            if search:
                logging.info("Returning to city.")
                self.click(Coordinates(100, 1000))
                self.wait_for_template(
                    "gui/map.png", crop=CropRegions(right=0.8, top=0.8)
                )
                sleep(3)

            self._click_help()
            self._research()
            self._click_resources()
            self._build()
            self._click_help()
            self._collect_troops()
            self._recruit_troops()
            self._click_help()
            self._alliance_research_and_gift()
            self._gather_resources()
            sleep(10)

    def _build(self) -> None:
        logging.info("Building.")
        button_1 = Coordinates(80, 220)
        button_2 = Coordinates(80, 350)

        try:
            self._handle_build_button(button_1)
        except GameTimeoutError:
            pass
        try:
            self._handle_build_button(button_2)
        except GameTimeoutError:
            pass

    def _handle_build_button(self, button_coordinates: Coordinates) -> None:
        self.click(button_coordinates)
        sleep(1)
        _, x, y = self.wait_for_any_template(
            templates=[
                "build/double_arrow_button.png",
                "build/double_arrow_button2.png",
            ],
            timeout=5,
        )
        self.click(Coordinates(x, y))
        x, y = self.wait_for_template("build/upgrade.png")
        self.click(Coordinates(x, y))
        sleep(2)

    def _center_city_view_by_using_research(self) -> None:
        logging.info("Center City View by using research.")
        research_btn = self.wait_for_template(
            "gui/left_side_research.png",
            crop=CropRegions(right=0.8, top=0.3, bottom=0.4),
            timeout=5,
            threshold=0.7,
        )
        self.click(Coordinates(*research_btn))
        sleep(0.5)
        x_button = self.game_find_template_match("gui/x.png")
        if x_button:
            self.click(Coordinates(*x_button))
            sleep(0.5)
        else:
            self.click(Coordinates(80, 700))

    def _research(self) -> None:
        logging.info("Starting Research.")
        try:
            research_btn = self.wait_for_template(
                "gui/left_side_research.png",
                crop=CropRegions(right=0.8, top=0.3, bottom=0.4),
                timeout=5,
                threshold=0.7,
            )

            self.click(Coordinates(*research_btn))
            self.wait_for_template("research/military.png", timeout=5)

            def click_and_hope_research_pops_up() -> tuple[int, int] | None:
                for y in y_coords:
                    self.click(Coordinates(1250, y))
                    sleep(2)
                    result = self.game_find_template_match("research/research.png")
                    if result:
                        return result
                return None

            y_coords = [250, 450, 550, 650, 850]
            research = click_and_hope_research_pops_up()

            if not research:
                military = self.game_find_template_match("research/military.png")
                if not military:
                    self.press_back_button()
                    sleep(2)
                    return
                self.click(Coordinates(*military))
                sleep(1)
                research = self.game_find_template_match("research/research.png")

            if research:
                self.click(Coordinates(*research))
            else:
                self.press_back_button()
            sleep(2)
            return
        except GameTimeoutError:
            return None

    def _recruit_troops(self) -> None:
        logging.info("Recruiting Troops.")
        try:
            while True:
                btn = self.wait_for_template(
                    "gui/left_side_recruit.png",
                    crop=CropRegions(right=0.8, top=0.4, bottom=0.3),
                    timeout=5,
                    threshold=0.7,
                )
                self.click(Coordinates(*btn))
                x, y = self.wait_for_template(
                    "recruitment/recruit.png",
                    crop=CropRegions(left=0.5, top=0.6),
                    timeout=5,
                )
                self.click(Coordinates(x, y))
                sleep(2)
        except GameTimeoutError:
            return None

    def _collect_troops(self) -> None:
        self._center_city_view_by_using_research()
        logging.info("Collecting Troops.")
        not_found_count = 0
        max_count = 5
        while not_found_count < max_count:
            result = self.find_any_template(
                [
                    "recruitment/t2/air.png",
                    "recruitment/t2/earth.png",
                    "recruitment/t2/fire.png",
                    "recruitment/t2/water.png",
                    "recruitment/t1/air.png",
                    "recruitment/t1/earth.png",
                    "recruitment/t1/fire.png",
                    "recruitment/t1/water.png",
                ]
            )
            if result is None:
                not_found_count += 1
                sleep(0.1)
                continue
            _, x, y = result
            self.click(Coordinates(x, y))

    def _gather_resources(self) -> None:
        logging.info("Gathering Resources.")
        search = self.game_find_template_match(
            "gathering/search.png",
            crop=CropRegions(right=0.8, top=0.6),
        )
        if not search:
            game_map = self.game_find_template_match("gui/map.png")
            if not game_map:
                logging.warning("Map not found skipping resource gathering.")
                return
            self.click(Coordinates(*game_map))
            search = self.wait_for_template(
                "gathering/search.png",
                crop=CropRegions(right=0.8, top=0.6),
            )

        try:
            self._start_gathering(Coordinates(*search))
        except GameTimeoutError as e:
            logging.warning(f"{e}")
        return

    def _start_gathering(self, search_coordinates: Coordinates) -> None:
        while not self.find_any_template(
            templates=[
                "gathering/troop_max_3.png",
            ],
            crop=CropRegions(left=0.8, bottom=0.5),
        ):
            self.click(search_coordinates)

            nodes = [
                "gathering/farmland.png",
                "gathering/logging_area.png",
                "gathering/mining_site.png",
                "gathering/gold_mine.png",
            ]

            node = nodes[self.gather_count % len(nodes)]

            x, y = self.wait_for_template(node)
            self.click(Coordinates(x, y))
            search_button = self.wait_for_template("gui/search.png")
            sleep(0.5)
            self.click(Coordinates(*search_button))
            sleep(5)
            self.click(Coordinates(960, 520))
            x, y = self.wait_for_template("gui/gather.png")
            sleep(0.5)
            self.click(Coordinates(x, y))
            sleep(0.5)
            x, y = self.wait_for_template("gui/create_new_troop.png")
            sleep(0.5)
            self.click(Coordinates(x, y))
            x, y = self.wait_for_template("gui/march.png")
            sleep(0.5)
            self.click(Coordinates(x, y))
            sleep(1)
            self.gather_count += 1
        logging.info("Troops already dispatched.")

    def _alliance_research_and_gift(self) -> None:
        logging.info("Alliance Research and Gift.")
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
        while x_btn := self.game_find_template_match("gui/x.png"):
            self.click(Coordinates(*x_btn))
            sleep(2)
        return

    def _handle_alliance_gift(self) -> None:
        treasure_chest = self.game_find_template_match("alliance/treasure_chest.png")
        if treasure_chest:
            self.click(Coordinates(*treasure_chest))
            sleep(0.2)
            self.click(Coordinates(*treasure_chest))
            sleep(6)
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
            for i in range(5):
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
        self._center_city_view_by_using_research()
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
                "alliance/help_request.png",
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
