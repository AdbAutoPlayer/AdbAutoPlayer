"""Avatar Realms Collide Main Module."""

import logging
from enum import StrEnum
from time import sleep, time

from adb_auto_player import Coordinates, CropRegions, GameTimeoutError
from adb_auto_player.command import Command
from adb_auto_player.games.avatar_realms_collide.base import AvatarRealmsCollideBase
from adb_auto_player.games.avatar_realms_collide.config import Config, ResourceEnum
from adb_auto_player.ipc.game_gui import GameGUIOptions, MenuOption


class ModeCategory(StrEnum):
    """Enumeration for mode categories used in the GUIs accordion menu."""

    ALL = "All"


class AvatarRealmsCollide(AvatarRealmsCollideBase):
    """Avatar Realms Collide Game."""

    gather_count: int = 0
    last_campaign_collection: float = 0
    last_alliance_research_and_gift: float = 0

    def auto_play(self) -> None:
        """Auto Play."""
        self.start_up(device_streaming=True)
        while True:
            try:
                self._navigate_to_city()
                self._auto_play_loop()
                sleep(10)
            except GameTimeoutError as e:
                logging.error(f"{e}")
                sleep(2)
                logging.info("Restarting...")

    def _navigate_to_city(self):
        while True:
            result = self.find_any_template(
                templates=[
                    "gathering/search.png",
                    "gui/map.png",
                    "gui/x.png",
                ]
            )
            if not result:
                continue
            template, x, y = result
            match template:
                case "gui/x.png":
                    self.click(Coordinates(x, y))
                    sleep(1)
                case "gathering/search.png":
                    logging.info("Returning to city")
                    self.click(Coordinates(100, 1000))
                    sleep(3)
                    _ = self.wait_for_template("gui/map.png", timeout=5)
                case "gui/map.png":
                    break
                case _:
                    self.press_back_button()
        sleep(3)

    def _auto_play_loop(self) -> None:
        self._click_help()
        if self.get_config().auto_play_config.research:
            self._research()

        self._click_resources()
        if self.get_config().auto_play_config.build:
            self._build()
            self._click_help()

        if self.get_config().auto_play_config.recruit_troops:
            self._recruit_troops()
            self._click_help()

        if self.get_config().auto_play_config.alliance_research_and_gifts:
            self._alliance_research_and_gift()

        if self.get_config().auto_play_config.collect_campaign_chest:
            self._collect_campaign_chest()

        self._use_free_scroll()

        if self.get_config().auto_play_config.gather_resources:
            self._gather_resources()

    def _use_free_scroll(self) -> None:
        self._center_city_view_by_using_research()
        scroll = self.game_find_template_match("altar/scroll.png")
        if not scroll:
            return
        self.click(Coordinates(*scroll))
        sleep(3)
        free = self.game_find_template_match("altar/free.png")
        if not free:
            self._navigate_to_city()
            return
        self.click(Coordinates(*free))
        ok = self.wait_for_template("altar/ok.png", timeout=15)
        self.click(Coordinates(*ok))
        sleep(1)
        self._navigate_to_city()

    def _collect_campaign_chest(self) -> None:
        one_hour = 3600
        if (
            self.last_campaign_collection
            and time() - self.last_campaign_collection < one_hour
        ):
            logging.info(
                "Skipping Campaign Chest collection: 1 hour cooldown period not over"
            )
            return

        logging.info("Collecting Campaign Chest")
        self.click(Coordinates(1420, 970))
        try:
            x, y = self.wait_for_template(
                "campaign/avatar_trail.png",
                timeout=5,
            )
            self.click(Coordinates(x, y))
        except GameTimeoutError as e:
            logging.error(f"{e}")
            return
        try:
            self.wait_for_template(
                "campaign/lobby_hero.png",
                timeout=5,
            )
            sleep(2)

            if chest := self.game_find_template_match("campaign/chest.png"):
                self.click(Coordinates(*chest))
                _ = self.wait_for_template("campaign/claim.png")
                while claim := self.game_find_template_match("campaign/claim.png"):
                    self.click(Coordinates(*claim))
                    sleep(0.5)
            self.last_campaign_collection = time()
        except GameTimeoutError as e:
            logging.error(f"{e}")

        self.press_back_button()
        self.wait_for_template("gui/map.png")
        sleep(1)
        return

    def _build(self) -> None:
        button_1 = Coordinates(80, 220)
        button_2 = Coordinates(80, 350)

        try:
            logging.info("Building Slot 1")
            self._handle_build_button(button_1)
        except GameTimeoutError:
            pass
        try:
            logging.info("Building Slot 2")
            self._handle_build_button(button_2)
        except GameTimeoutError:
            pass

    def _handle_build_button(self, button_coordinates: Coordinates) -> None:
        self.click(button_coordinates)
        _, x, y = self.wait_for_any_template(
            templates=[
                "build/double_arrow_button.png",
                "build/double_arrow_button2.png",
            ],
            timeout=5,
        )
        self.click(Coordinates(x, y))
        while upgrade := self.wait_for_template("build/upgrade.png", timeout=5):
            self.click(Coordinates(*upgrade))
            while x_btn := self.game_find_template_match("gui/x.png"):
                self.click(Coordinates(*x_btn))
                sleep(2)

    def _center_city_view_by_using_research(self) -> None:
        logging.info("Center City View by using research")
        x_button = self.game_find_template_match("gui/x.png")
        if x_button:
            self.click(Coordinates(*x_button))
            sleep(0.5)
        else:
            self.click(Coordinates(80, 700))

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
        logging.info("Starting Research")
        try:
            research_btn = self.wait_for_template(
                "gui/left_side_research.png",
                crop=CropRegions(right=0.8, top=0.3, bottom=0.4),
                timeout=5,
                threshold=0.7,
            )

            self.click(Coordinates(*research_btn))
            template, x, y = self.wait_for_any_template(
                templates=[
                    "research/military.png",
                    "research/economy.png",
                ],
                timeout=5,
            )
            sleep(2)
            if template == "research/military.png":
                self.click(Coordinates(x, y))

            def click_and_hope_research_pops_up() -> tuple[int, int] | None:
                for y_coord in y_coords:
                    self.click(Coordinates(1250, y_coord))
                    sleep(2)
                    result = self.game_find_template_match("research/research.png")
                    if result:
                        return result
                    if self.game_find_template_match("research/max_level.png"):
                        x_btn = self.game_find_template_match("gui/x.png")
                        if x_btn:
                            self.click(Coordinates(*x_btn))
                            sleep(2)
                return None

            y_coords = [250, 450, 550, 650, 850]
            for i in range(5):
                research = click_and_hope_research_pops_up()
                if research:
                    break
                self.swipe(500, 540, 400, 540)
                sleep(2)

            if not research:
                economy = self.game_find_template_match("research/economy.png")
                if not economy:
                    logging.error("Economy research not found")
                    self.press_back_button()
                    sleep(2)
                    return
                self.click(Coordinates(*economy))
                sleep(1)
                research = click_and_hope_research_pops_up()

            if research:
                self.click(Coordinates(*research))
            else:
                logging.error("No research found")
                self.press_back_button()
            sleep(2)
            return
        except GameTimeoutError:
            return None

    def _recruit_troops(self) -> None:
        logging.info("Recruiting Troops")
        try:
            btn = self.wait_for_template(
                "gui/left_side_recruit.png",
                crop=CropRegions(right=0.8, top=0.4, bottom=0.3),
                timeout=5,
                threshold=0.7,
            )

            for i in range(5):
                self.click(Coordinates(*btn))
                sleep(0.5)

            while True:
                sleep(1)
                x, y = self.wait_for_template(
                    "recruitment/recruit.png",
                    crop=CropRegions(left=0.5, top=0.6),
                    timeout=5,
                )
                self.click(Coordinates(x, y))
                sleep(1)
                btn = self.wait_for_template(
                    "gui/left_side_recruit.png",
                    crop=CropRegions(right=0.8, top=0.4, bottom=0.3),
                    timeout=5,
                    threshold=0.7,
                )
                self.click(Coordinates(*btn))
        except GameTimeoutError:
            return None

    def _gather_resources(self) -> None:
        if self._troops_are_dispatched():
            logging.info("All Troops dispatched skipping resource gathering")
            return
        logging.info("Gathering Resources")
        search = self.game_find_template_match(
            "gathering/search.png",
            crop=CropRegions(right=0.8, top=0.6),
        )
        if not search:
            game_map = self.game_find_template_match("gui/map.png")
            if not game_map:
                logging.warning("Map not found skipping resource gathering")
                return
            self.click(Coordinates(*game_map))
            search = self.wait_for_template(
                "gathering/search.png",
                crop=CropRegions(right=0.8, top=0.6),
            )
            sleep(2)
        try:
            self._start_gathering(Coordinates(*search))
        except GameTimeoutError as e:
            logging.warning(f"{e}")
        return

    def _troops_are_dispatched(self) -> bool:
        if self.find_any_template(
            templates=[
                "gathering/troop_max_3.png",
            ],
            crop=CropRegions(left=0.8, bottom=0.5),
        ):
            return True
        return False

    def _start_gathering(self, search_coordinates: Coordinates) -> None:
        while not self._troops_are_dispatched():
            self.click(search_coordinates)

            nodes = {
                "Food": "gathering/farmland.png",
                "Wood": "gathering/logging_area.png",
                "Stone": "gathering/mining_site.png",
                "Gold": "gathering/gold_mine.png",
            }
            resources: list[ResourceEnum] = (
                self.get_config().auto_play_config.gather_resources
            )

            resource = resources[self.gather_count % len(resources)]
            node = nodes[resource]
            x, y = self.wait_for_template(node, timeout=5)
            self.click(Coordinates(x, y))
            _ = self.wait_for_template("gui/search.png", timeout=5)
            sleep(1)
            search_button = self.wait_for_template("gui/search.png", timeout=5)
            self.click(Coordinates(*search_button))
            sleep(5)
            self.click(Coordinates(960, 520))
            x, y = self.wait_for_template("gui/gather.png", timeout=5)
            sleep(0.5)
            self.click(Coordinates(x, y))
            sleep(0.5)
            template, x, y = self.wait_for_any_template(
                templates=["gui/create_new_troop.png", "gui/march_blue.png"],
                timeout=5,
            )
            if template == "gui/march_blue.png":
                self.press_back_button()
                sleep(1)
                logging.warning("Troops already dispatched cancelling gathering")
                return
            sleep(0.5)
            self.click(Coordinates(x, y))
            x, y = self.wait_for_template("gui/march.png", timeout=5)
            sleep(0.5)
            self.click(Coordinates(x, y))
            sleep(3)
            self.gather_count += 1
        return

    def _alliance_research_and_gift(self) -> None:
        one_hour = 3600
        if (
            self.last_alliance_research_and_gift
            and time() - self.last_alliance_research_and_gift < one_hour
        ):
            logging.info(
                "Skipping Alliance Research and Gift: 1 hour cooldown period not over"
            )
            return

        logging.info("Alliance Research and Gift")
        if not self.game_find_template_match("gui/map.png"):
            logging.warning("Map not found skipping alliance research and gift")
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
        self.last_alliance_research_and_gift = time()
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
        while claim := self.game_find_template_match("gui/claim.png"):
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
            logging.warning("Alliance Research window not found")
            return None

        def find_or_swipe(template: str):
            for _ in range(6):
                match = self.game_find_template_match(template)
                if match:
                    return match
                self.swipe(800, 540, 300, 540)
                sleep(2)
            return None

        recommended = find_or_swipe("alliance/recommended.png")
        if not recommended:
            self.game_find_template_match("alliance/research_territory.png")
            recommended = find_or_swipe("alliance/recommended.png")

        if not recommended:
            self.game_find_template_match("alliance/research_warfare.png")
            recommended = find_or_swipe("alliance/recommended.png")

        if not recommended:
            logging.warning("No recommended alliance research")
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
                "alliance/help_request.png",
                "alliance/help_button.png",
            ],
            threshold=0.7,
            crop=CropRegions(top=0.1, right=0.1),
        ):
            _, x, y = result
            self.click(Coordinates(x, y))
            sleep(2)

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
