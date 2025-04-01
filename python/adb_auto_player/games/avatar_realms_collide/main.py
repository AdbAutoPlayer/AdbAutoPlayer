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
                    "gui/cancel.png",
                    "gui/ok.png",
                    "gathering/search.png",
                    "gui/map.png",
                    "gui/x.png",
                ]
            )
            if not result:
                self.press_back_button()
                sleep(3)
                continue
            template, x, y = result
            match template:
                case "gui/x.png" | "gui/cancel.png" | "gui/ok.png":
                    self.click(Coordinates(x, y))
                    sleep(2)
                case "gathering/search.png":
                    logging.info("Returning to city")
                    self.click(Coordinates(100, 1000))
                    sleep(3)
                    try:
                        _ = self.wait_for_template("gui/map.png", timeout=5)
                    except GameTimeoutError:
                        # happens on a disconnect
                        self.click(Coordinates(1560, 970))
                case "gui/map.png":
                    break
        sleep(3)

    def _attempt_to_reconnect(self) -> None:
        logging.info("Attempting to reconnect...")
        self.click(Coordinates(1560, 970))
        try:
            while ok := self.wait_for_template("gui/ok.png", timeout=5):
                self.click(Coordinates(*ok))
                sleep(1)
        except GameTimeoutError:
            return
        return

    def _auto_play_loop(self) -> None:
        self._alliance_research_and_gift()
        self._click_resources()
        self._build()
        self._click_help()

        if self.get_config().auto_play_config.recruit_troops:
            self._recruit_troops()
            self._click_help()
        else:
            logging.info("Recruiting Troops disabled")

        self._collect_campaign_chest()

        self._use_free_scroll()

        self._gather_resources()
        self._navigate_to_city()
        self._research()

    def _use_free_scroll(self) -> None:
        if not self.get_config().auto_play_config.collect_free_scrolls:
            logging.info("Collecting Free Scrolls disabled")
            return

        self._center_city_view_by_using_research()
        logging.info("Collecting free scroll")
        scroll = self.find_any_template(
            [
                "altar/scroll.png",
                "altar/scroll2.png",
            ],
            threshold=0.7,
        )
        if not scroll:
            return
        _, x, y = scroll
        self.click(Coordinates(x, y))
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

    def _healing(self) -> None:
        try:
            while heal_complete := self.wait_for_template(
                template="healing/complete.png",
                timeout=5,
            ):
                self.click(Coordinates(*heal_complete))
                sleep(1)
        except GameTimeoutError:
            return
        return

    def _collect_campaign_chest(self) -> None:
        if not self.get_config().auto_play_config.collect_campaign_chest:
            logging.info("Collecting Campaign Chest disabled")
            return

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
                timeout=15,
                threshold=0.6,
            )
            sleep(2)

            if chest := self.game_find_template_match("campaign/chest.png"):
                self.click(Coordinates(*chest))
                _ = self.wait_for_template("campaign/claim.png")
                while claim := self.game_find_template_match("campaign/claim.png"):
                    self.click(Coordinates(*claim))
                    sleep(1)
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

        if self.get_config().auto_play_config.building_slot_1:
            try:
                logging.info("Building Slot 1")
                self._handle_build_button(button_1)
            except GameTimeoutError:
                pass
        else:
            logging.info("Building Slot 1 disabled")
        if self.get_config().auto_play_config.building_slot_2:
            try:
                logging.info("Building Slot 2")
                self._handle_build_button(button_2)
            except GameTimeoutError:
                pass
        else:
            logging.info("Building Slot 2 disabled")

    def _handle_build_button(self, button_coordinates: Coordinates) -> None:
        self.click(button_coordinates)
        _, x, y = self.wait_for_any_template(
            templates=[
                "build/double_arrow_button.png",
                "build/double_arrow_button2.png",
            ],
            threshold=0.7,
            timeout=5,
        )
        self.click(Coordinates(x, y))
        while upgrade := self.wait_for_template("build/upgrade.png", timeout=5):
            self.click(Coordinates(*upgrade))
            self._handle_replenish_all("build/upgrade.png")
            while x_btn := self.game_find_template_match("gui/x.png"):
                self.click(Coordinates(*x_btn))
                sleep(2)

    def _center_city_view_by_using_research(self) -> None:
        logging.info("Center City View by using research")
        x_button = self.game_find_template_match("gui/x.png")
        if x_button:
            self.click(Coordinates(*x_button))
            sleep(1)
        else:
            self.click(Coordinates(80, 700))

        research_btn = self.wait_for_template(
            "gui/left_side_research.png",
            crop=CropRegions(right=0.8, top=0.3, bottom=0.4),
            timeout=5,
            threshold=0.6,
        )
        self.click(Coordinates(*research_btn))
        sleep(1)
        x_button = self.game_find_template_match("gui/x.png")
        if x_button:
            self.click(Coordinates(*x_button))
            sleep(1)
        else:
            self.click(Coordinates(80, 700))

    def _research(self) -> None:  # noqa: PLR0915
        if not self.get_config().auto_play_config.research:
            logging.info("Research disabled")
            return

        logging.info("Starting Research")
        try:
            research_btn = self.wait_for_template(
                "gui/left_side_research.png",
                crop=CropRegions(right=0.8, top=0.3, bottom=0.4),
                timeout=5,
                threshold=0.7,
            )

            self.click(Coordinates(*research_btn))
            sleep(1)
            self.click(Coordinates(*research_btn))
            template, x, y = self.wait_for_any_template(
                templates=[
                    "research/military.png",
                    "research/economy.png",
                ],
                timeout=5,
            )
            sleep(2)

            if self.get_config().auto_play_config.military_first:
                logging.info("Checking Military Research first")
                if template == "research/military.png":
                    self.click(Coordinates(x, y))
            elif template == "research/economy.png":
                logging.info("Checking Economy Research first")
                self.click(Coordinates(x, y))

            def click_and_hope_research_pops_up() -> tuple[int, int] | None:
                y_coords = [250, 450, 550, 650, 850]
                for y_coord in y_coords:
                    self.click(Coordinates(1250, y_coord))
                    sleep(2)
                    result = self.game_find_template_match("research/research.png")
                    if result:
                        return result

                    x_btn = self.game_find_template_match(
                        "gui/x.png", crop=CropRegions(right=0.1)
                    )
                    if x_btn:
                        self.click(Coordinates(*x_btn))
                        sleep(2)
                return None

            def try_to_find_research() -> tuple[int, int] | None:
                research_coords = click_and_hope_research_pops_up()
                for i in range(5):
                    if research_coords:
                        return research_coords
                    self.swipe(500, 540, 400, 540)
                    sleep(2)
                    research_coords = click_and_hope_research_pops_up()
                logging.warning("No research found, swiping back")
                for _ in range(5):
                    self.swipe(400, 540, 500, 540)
                return research_coords

            research = try_to_find_research()
            if not research:
                if self.get_config().auto_play_config.military_first:
                    btn = self.game_find_template_match("research/economy.png")
                else:
                    btn = self.game_find_template_match("research/military.png")

                if not btn:
                    self.press_back_button()
                    sleep(2)
                    return

                self.click(Coordinates(*btn))
                sleep(1)
                research = try_to_find_research()

            if research:
                self.click(Coordinates(*research))
                self._handle_replenish_all("research/research.png")
            else:
                logging.error("No research found")
                self.press_back_button()
            sleep(2)
            return
        except GameTimeoutError:
            return None

    def _handle_replenish_all(self, button_template: str) -> None:
        try:
            replenish = self.wait_for_template(
                "gui/replenish_all.png",
                timeout=3,
            )
            self.click(Coordinates(*replenish))
            btn = self.wait_for_template(button_template, timeout=5)
            self.click(Coordinates(*btn))
        except GameTimeoutError:
            return
        return

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
                sleep(1)

            while True:
                sleep(1)
                x, y = self.wait_for_template(
                    "recruitment/recruit.png",
                    crop=CropRegions(left=0.5, top=0.6),
                    timeout=5,
                )
                self.click(Coordinates(x, y))
                self._handle_replenish_all("recruitment/recruit.png")
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
        if not self.get_config().auto_play_config.gather_resources:
            logging.info("Gathering Resources disabled")
            return

        if self._troops_are_dispatched():
            logging.info("All Troops dispatched skipping resource gathering")
            return

        logging.info("Gathering Resources")
        search = self.game_find_template_match(
            "gathering/search.png",
            crop=CropRegions(right=0.8, top=0.6),
            threshold=0.7,
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
        try:
            self.wait_for_any_template(
                templates=[
                    # "gathering/troop_max_5.png",
                    "gathering/troop_max_4.png",
                    "gathering/troop_max_3.png",
                    "gathering/troop_max_2.png",
                ],
                crop=CropRegions(left=0.8, bottom=0.5),
                timeout=3,
            )
        except GameTimeoutError:
            return False
        return True

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
            search_button = self.wait_for_template(
                "gui/search.png",
                threshold=0.7,
                timeout=5,
            )
            self.click(Coordinates(*search_button))
            sleep(1)
            try:
                self.wait_until_template_disappears(
                    "gui/search.png",
                    threshold=0.7,
                    timeout=3,
                )
            except GameTimeoutError:
                logging.warning(f"{resource} not found, trying next one")
                self.press_back_button()
                self.gather_count += 1
                sleep(1)
                continue
            sleep(4)
            self.click(Coordinates(960, 520))
            x, y = self.wait_for_template("gui/gather.png", timeout=5)
            sleep(1)
            self.click(Coordinates(x, y))
            sleep(1)
            template, x, y = self.wait_for_any_template(
                templates=["gui/create_new_troop.png", "gui/march_blue.png"],
                timeout=5,
            )
            if template == "gui/march_blue.png":
                self.press_back_button()
                sleep(1)
                logging.warning("Troops already dispatched cancelling gathering")
                return
            sleep(1)
            self.click(Coordinates(x, y))
            x, y = self.wait_for_template("gui/march.png", timeout=5)
            sleep(1)
            self.click(Coordinates(x, y))
            sleep(3)
            self.gather_count += 1
        return

    def _alliance_research_and_gift(self) -> None:
        if (
            not self.get_config().auto_play_config.alliance_research
            and not self.get_config().auto_play_config.alliance_gifts
        ):
            logging.info("Alliance Research & Gifts disabled.")
            return

        one_hour = 3600
        if (
            self.last_alliance_research_and_gift
            and time() - self.last_alliance_research_and_gift < one_hour
        ):
            logging.info(
                "Skipping Alliance Research and Gift: 1 hour cooldown period not over"
            )
            return

        logging.info("Opening Alliance window")
        if not self.game_find_template_match("gui/map.png"):
            logging.warning("Map not found skipping alliance research and gift")
            return
        self.click(Coordinates(1560, 970))
        self.wait_for_template("alliance/alliance_shop.png")
        sleep(2)

        if self.get_config().auto_play_config.alliance_research:
            logging.info("Opening Alliance Research window")
            research = self.game_find_template_match("alliance/research.png")
            if research:
                self.click(Coordinates(*research))
                self._handle_alliance_research()
            else:
                logging.info("Alliance Research button not found")
        else:
            logging.info("Alliance Research disabled")
        if self.get_config().auto_play_config.alliance_gifts:
            logging.info("Opening Alliance Gifts window")
            gift = self.game_find_template_match("alliance/gift.png")
            if gift:
                self.click(Coordinates(*gift))
                sleep(2)
                self._handle_alliance_gift()
        else:
            logging.info("Alliance Gifts disabled")
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
                sleep(1)
        claim_all = self.game_find_template_match("alliance/claim_all.png")
        if claim_all:
            self.click(Coordinates(*claim_all))
            sleep(2)
        gift_chest = self.game_find_template_match("alliance/gift_chest.png")
        if not gift_chest:
            return
        self.click(Coordinates(*gift_chest))
        sleep(1)
        while claim := self.game_find_template_match("gui/claim.png"):
            self.click(Coordinates(*claim))
            sleep(1)
            refresh = self.game_find_template_match("alliance/gift_chest_refresh.png")
            if refresh:
                self.click(Coordinates(*refresh))
                sleep(1)
        self.press_back_button()
        sleep(1)
        return

    def _handle_alliance_research(self) -> None:
        try:
            self.wait_for_any_template(
                templates=[
                    "alliance/research_development.png",
                    "alliance/research_territory.png",
                    "alliance/research_warfare.png",
                ],
                timeout=5,
            )
        except GameTimeoutError:
            logging.warning("Alliance Research window not found")
            return None

        def find_or_swipe_recommended() -> tuple[int, int] | None:
            for _ in range(6):
                match = self.game_find_template_match(
                    "alliance/research_recommended.png",
                    threshold=0.8,
                    crop=CropRegions(left=0.2, right=0.2, top=0.1, bottom=0.1),
                )
                if match:
                    return match
                sleep(2)
            logging.warning("Recommended research not found, swiping back")
            for _ in range(6):
                self.swipe(300, 540, 800, 540)
            return None

        recommended = find_or_swipe_recommended()

        if not recommended:
            logging.warning("No recommended alliance research")
            return
        x, y = recommended
        self.click(Coordinates(x + 80, y - 150))
        sleep(2)
        while donate := self.game_find_template_match(
            "alliance/research_donate.png", crop=CropRegions(left=0.6, top=0.6)
        ):
            for i in range(10):
                self.click(Coordinates(*donate))
                sleep(0.1)
            self._handle_replenish_all("alliance/research_donate.png")
        x_button = self.game_find_template_match("gui/x.png")
        if x_button:
            self.click(Coordinates(*x_button))
            sleep(1)
        self.press_back_button()
        sleep(1)
        return

    def _click_resources(self) -> None:
        self._center_city_view_by_using_research()
        logging.info("Clicking resources")
        while result := self.find_any_template(
            [
                "gui/ok.png",
                "harvest/food.png",
                "harvest/wood.png",
                "harvest/stone.png",
                "harvest/gold.png",
            ],
            threshold=0.7,
            crop=CropRegions(top=0.3, left=0.1, right=0.1, bottom=0.1),
        ):
            _, x, y = result
            self.click(Coordinates(x, y))
            sleep(1)

    def _click_help(self) -> None:
        logging.info("Clicking help")
        no_help_found_count = 0
        max_count = 3
        while no_help_found_count < max_count:
            result = self.find_any_template(
                [
                    "alliance/help_request.png",
                    "alliance/help_request2.png",
                    "alliance/help_button.png",
                    "alliance/help_bubble.png",
                ],
                threshold=0.7,
                crop=CropRegions(
                    left=0.1,
                    right=0.1,
                    top=0.1,
                    bottom=0.1,
                ),
            )
            if not result:
                no_help_found_count += 1
                sleep(1)
                continue
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
