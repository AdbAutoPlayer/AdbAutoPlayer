"""Avatar Realms Collide Main Module."""

import logging
from collections.abc import Callable
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


class NoRechargeableAPError(Exception):
    """No rechargeable AP (pots or free AP)."""

    pass


class AvatarRealmsCollide(AvatarRealmsCollideBase):
    """Avatar Realms Collide Game."""

    expedition_count: int = 0
    gather_count: int = 0
    last_campaign_collection: float = 0
    last_alliance_research_and_gift: float = 0
    unchecked_hold_position_after_attack: bool = False
    recruitment_max_tier: int = 6
    no_ap: bool = False

    def auto_play(self) -> None:
        """Auto Play."""
        self.start_up(device_streaming=True)
        while True:
            try:
                self._navigate_to_city()
                self._auto_play_loop()
                sleep(10)
            except NoRechargeableAPError:
                logging.error("AP cannot be recharged disabling Expedition")
                self.no_ap = True
            except GameTimeoutError as e:
                logging.error(f"{e}")
                sleep(2)
                logging.info("Restarting...")

    def _navigate_to_city(self):
        logging.info("Navigating to city")
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
                    self.tap(Coordinates(x, y))
                    sleep(2)
                case "gathering/search.png":
                    self.tap(Coordinates(100, 1000))
                    sleep(3)
                    try:
                        _ = self.wait_for_template("gui/map.png", timeout=10)
                    except GameTimeoutError:
                        # happens on a disconnect
                        self.tap(Coordinates(1560, 970))
                case "gui/map.png":
                    break
        sleep(3)

    def _auto_play_loop(self) -> None:
        def safe_execute(action_func: Callable[[], None]):
            try:
                action_func()
            except GameTimeoutError as e:
                logging.error(f"{e}")
                self._navigate_to_city()

        self._build()
        self._click_help()

        config = self.get_config().auto_play_config

        if config.research:
            safe_execute(self._research)
            self._click_help()
        else:
            logging.info("Research disabled")

        self._click_resources()

        if config.recruit_troops:
            safe_execute(self._recruit_troops)
            self._click_help()
        else:
            logging.info("Recruiting Troops disabled")

        for action in [
            self._collect_campaign_chest,
            self._use_free_scroll,
            self._alliance_research_and_gift,
        ]:
            safe_execute(action)

        self._expedition()
        self._navigate_to_city()
        self._gather_resources()

    def _recharge_ap(self) -> bool:
        sleep(1)
        go = self.game_find_template_match("expedition/go.png")
        if not go:
            return False
        self.tap(Coordinates(*go))
        use = self.game_find_template_match("expedition/use.png")
        if use:
            self.tap(Coordinates(*use))
            sleep(1)
            self.press_back_button()
            return True
        raise NoRechargeableAPError()

    def _uncheck_hold_position_after_attack(self) -> None:
        if (
            self.unchecked_hold_position_after_attack
            or self.get_config().auto_play_config.skip_hold_position_check
        ):
            return

        logging.info("Unchecking Hold Position after Attack")
        count = 0
        max_attempts = 3
        while count < max_attempts:
            try:
                search = self.wait_for_template(
                    "gathering/search.png",
                    crop=CropRegions(right=0.8, top=0.6),
                    timeout=5,
                )
                self.tap(Coordinates(*search))
                shattered_skulls = self.wait_for_template(
                    "expedition/shattered_skulls.png"
                )
                self.tap(Coordinates(*shattered_skulls))
                while True:
                    search = self.wait_for_template(
                        "gui/search.png",
                        timeout=5,
                    )
                    self.tap(Coordinates(*search))
                    sleep(1)
                    self.tap(Coordinates(1920 // 2, 1080 // 2))
                    template, x, y = self.wait_for_any_template(
                        [
                            "expedition/attack.png",
                            "gui/ok.png",
                        ],
                        timeout=5,
                    )

                    if template == "gui/ok.png":
                        self.tap(Coordinates(x, y))
                        sleep(2)
                        minus = self.game_find_template_match("expedition/minus.png")

                        if minus:
                            self.tap(Coordinates(*minus))
                        continue
                    break

                checked_box = self.game_find_template_match(
                    "expedition/checked_box.png",
                )
                if checked_box:
                    self.tap(Coordinates(*checked_box))
                self.press_back_button()
                self.unchecked_hold_position_after_attack = True
                break
            except GameTimeoutError:
                count += 1
        return

    def _expedition(self) -> None:  # noqa: PLR0915 PLR0912
        if not self.get_config().auto_play_config.expedition or self.no_ap:
            logging.info("Expedition disabled")
            return

        if self._troops_are_dispatched():
            logging.info("All Troops dispatched skipping expedition")
            return

        logging.info("Checking Expedition")
        gui_map = self.game_find_template_match(
            "gui/map.png",
            crop=CropRegions(right=0.8, top=0.6),
            threshold=0.7,
        )

        if gui_map:
            self.tap(Coordinates(*gui_map))
            _ = self.wait_for_template(
                "gathering/search.png",
                crop=CropRegions(right=0.8, top=0.6),
            )

        self._uncheck_hold_position_after_attack()

        self.tap(Coordinates(80, 230))
        _ = self.wait_for_template("expedition/expedition.png")
        sleep(5)

        # types = ["cave", "scout", "troops", "chest"]
        # colors = ["green", "blue", "purple", "orange"]
        # templates = [f"expedition/{t}/{c}.png" for t in types for c in colors]

        templates = [
            "expedition/chest/green.png",
            "expedition/chest/blue.png",
            "expedition/chest/purple.png",
            "expedition/chest/orange.png",
            "expedition/cave/green.png",
            "expedition/cave/blue.png",
            "expedition/cave/purple.png",
            "expedition/cave/orange.png",
            "expedition/scout/green.png",
            "expedition/scout/blue.png",
            "expedition/scout/purple.png",
            # "expedition/scout/orange.png",
            "expedition/troops/green.png",
            "expedition/troops/blue.png",
            # "expedition/troops/purple.png",
            "expedition/troops/orange.png",
        ]

        while True:
            if not self.game_find_template_match("expedition/expedition.png"):
                self.tap(Coordinates(80, 230))
                self.wait_for_template("expedition/expedition.png", timeout=10)

            try:
                result = self.wait_for_any_template(
                    templates=templates,
                    threshold=0.7,
                    timeout=10,
                )
            except GameTimeoutError:
                logging.info("No Expeditions found")
                return
            template, x, y = result

            max_attempts = 3
            attempt = 0
            while attempt < max_attempts and not self.find_any_template(
                [
                    "gui/ok.png",
                    "expedition/go.png",
                ]
            ):
                attempt += 1
                self.tap(Coordinates(x, y))
                sleep(3)

            button_result = self.find_any_template(
                [
                    "gui/ok.png",
                    "expedition/go.png",
                ]
            )

            if not button_result:
                raise GameTimeoutError("Could not find ok or go button.")

            template, x, y = button_result

            if template == "gui/ok.png":
                sleep(1)
                self.tap(Coordinates(x, y))
                self.expedition_count += 1
                continue

            self.tap(Coordinates(x, y))
            sleep(1)
            timeout_count = 0
            max_timeout_count = 2
            while timeout_count < max_timeout_count:
                self.tap(Coordinates(1920 // 2, 1080 // 2))
                try:
                    template, x, y = self.wait_for_any_template(
                        templates=[
                            "expedition/survey.png",
                            "expedition/enter.png",
                            "expedition/murong.png",
                        ],
                        timeout=5,
                    )
                    match template:
                        case "expedition/enter.png":
                            self.tap(Coordinates(x, y))
                            if self._recharge_ap():
                                self.tap(Coordinates(x, y))
                            start = self.wait_for_template(
                                "expedition/start.png", timeout=10
                            )
                            self.tap(Coordinates(*start))
                            ok = self.wait_for_template("gui/ok.png", timeout=10)
                            self.tap(Coordinates(*ok))
                            self.expedition_count += 1
                            logging.info(
                                f"Expeditions completed: {self.expedition_count}"
                            )
                            sleep(3)
                            break
                        case "expedition/survey.png":
                            self.tap(Coordinates(x, y))
                            if self._recharge_ap():
                                self.tap(Coordinates(x, y))
                            self.expedition_count += 1
                            break
                        case "expedition/murong.png":
                            attack = self.game_find_template_match(
                                "expedition/attack.png"
                            )
                            if not attack:
                                continue
                            self.tap(Coordinates(*attack))
                            template, x, y = self.wait_for_any_template(
                                [
                                    "expedition/create_a_new_troop.png",
                                    "expedition/march_troops.png",
                                ],
                                threshold=0.7,
                                timeout=5,
                            )

                            self.tap(Coordinates(x, y))

                            if template == "expedition/create_a_new_troop.png":
                                x, y = self.wait_for_template(
                                    "expedition/march.png",
                                    threshold=0.7,
                                    timeout=5,
                                )
                                self.tap(Coordinates(x, y))

                            if self._recharge_ap():
                                self.tap(Coordinates(x, y))

                            self.expedition_count += 1
                            logging.info(
                                f"Expeditions completed: {self.expedition_count}"
                            )
                            logging.info("Waiting 90 seconds.")
                            sleep(90)  # make sure it is dead
                            break
                except GameTimeoutError:
                    timeout_count += 1
                    continue
        return

    def _use_free_scroll(self) -> None:
        if not self.get_config().auto_play_config.collect_free_scrolls:
            logging.info("Collecting Free Scrolls disabled")
            return

        self._center_city_view_on_research_lab()
        logging.info("Looking for free Scroll")
        scroll = self.find_any_template(
            [
                "altar/scroll.png",
                "altar/scroll2.png",
            ],
            threshold=0.7,
        )
        if not scroll:
            logging.info("Free Scroll not found")
            return

        logging.info("Collecting free Scroll")
        _, x, y = scroll
        self.tap(Coordinates(x, y))
        sleep(3)
        free = self.game_find_template_match("altar/free.png")
        if not free:
            self._navigate_to_city()
            return
        self.tap(Coordinates(*free))
        ok = self.wait_for_template("altar/ok.png", timeout=15)
        self.tap(Coordinates(*ok))
        sleep(1)
        self._navigate_to_city()

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

        logging.info("Checking Campaign Chest")
        self.tap(Coordinates(1420, 970))
        x, y = self.wait_for_template(
            "campaign/avatar_trail.png",
            threshold=0.7,
            timeout=10,
        )
        self.tap(Coordinates(x, y))

        self.wait_for_template(
            "campaign/lobby_hero.png",
            timeout=15,
            threshold=0.6,
        )
        sleep(2)

        if chest := self.game_find_template_match(
            "campaign/chest.png",
            threshold=0.7,
        ):
            self.tap(Coordinates(*chest))
            sleep(3)
        while claim := self.game_find_template_match(
            "campaign/claim.png",
            threshold=0.7,
        ):
            self.tap(Coordinates(*claim))
            logging.info("Claimed Campaign Chest")
            sleep(1)
        self.last_campaign_collection = time()
        self.press_back_button()
        _ = self.wait_for_template(
            "gui/map.png",
            crop=CropRegions(right=0.8, top=0.8),
            timeout=10,
            threshold=0.7,
        )
        sleep(1)
        return

    def _build(self) -> None:
        button_1 = Coordinates(80, 220)
        button_2 = Coordinates(80, 350)

        if self.get_config().auto_play_config.building_slot_1:
            try:
                logging.info("Checking Build Slot 1")
                self._handle_build_button(button_1)
            except GameTimeoutError:
                pass
        else:
            logging.info("Build Slot 1 disabled")
        if self.get_config().auto_play_config.building_slot_2:
            try:
                logging.info("Checking Build Slot 2")
                self._handle_build_button(button_2)
            except GameTimeoutError:
                pass
        else:
            logging.info("Build Slot 2 disabled")

    def _handle_build_button(self, button_coordinates: Coordinates) -> None:
        self.tap(button_coordinates)
        _, x, y = self.wait_for_any_template(
            templates=[
                "build/double_arrow_button.png",
                "build/double_arrow_button2.png",
            ],
            threshold=0.7,
            timeout=10,
        )
        self.tap(Coordinates(x, y))
        while upgrade := self.wait_for_template("build/upgrade.png", timeout=10):
            logging.info("Upgrading Building")
            self.tap(Coordinates(*upgrade))
            self._handle_replenish_all("build/upgrade.png")
            if self.get_config().auto_play_config.purchase_seal_of_solidarity:
                self._purchase_seal_of_solidarity_if_needed()
        while x_btn := self.game_find_template_match("gui/x.png"):
            self.tap(Coordinates(*x_btn))
            sleep(2)

    def _center_city_view_on_research_lab(self) -> None:
        logging.info("Center City View on Research Lab")
        x_button = self.game_find_template_match("gui/x.png")
        if x_button:
            self.tap(Coordinates(*x_button))
            sleep(1)
        else:
            self.tap(Coordinates(80, 700))

        _ = self.wait_for_template(
            "gui/map.png",
            crop=CropRegions(right=0.8, top=0.8),
            timeout=10,
            threshold=0.7,
        )
        self.tap(Coordinates(80, 480))
        sleep(1)
        x_button = self.game_find_template_match("gui/x.png")
        if x_button:
            self.tap(Coordinates(*x_button))
            sleep(1)
        else:
            self.tap(Coordinates(80, 700))

    def _research(self) -> None:  # noqa: PLR0915
        logging.info("Checking Research")
        _ = self.wait_for_template(
            "gui/map.png",
            crop=CropRegions(right=0.8, top=0.8),
            timeout=10,
            threshold=0.7,
        )

        self.tap(Coordinates(80, 480))
        sleep(1)
        self.tap(Coordinates(80, 480))
        try:
            template, x, y = self.wait_for_any_template(
                templates=[
                    "research/military.png",
                    "research/economy.png",
                ],
                timeout=10,
            )
        except GameTimeoutError:
            return None
        sleep(2)

        if self.get_config().auto_play_config.military_first:
            logging.info("Checking Military Research first")
            if template == "research/military.png":
                self.tap(Coordinates(x, y))
        elif template == "research/economy.png":
            logging.info("Checking Economy Research first")
            self.tap(Coordinates(x, y))

        def click_and_hope_research_pops_up() -> tuple[int, int] | None:
            y_coords = [250, 450, 550, 650, 850]
            for y_coord in y_coords:
                self.tap(Coordinates(1250, y_coord))
                sleep(2)
                result = self.game_find_template_match("research/research.png")
                if result:
                    return result

                x_btn = self.game_find_template_match(
                    "gui/x.png", crop=CropRegions(right=0.1)
                )
                if x_btn:
                    self.tap(Coordinates(*x_btn))
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
            template = "research/military.png"
            if self.get_config().auto_play_config.military_first:
                template = "research/economy.png"

            btn = self.game_find_template_match(template)
            if not btn:
                self.press_back_button()
                sleep(2)
                return

            self.tap(Coordinates(*btn))
            sleep(1)
            research = try_to_find_research()

        if research:
            self.tap(Coordinates(*research))
            self._handle_replenish_all("research/research.png")
        else:
            logging.error("No research found")
            self.press_back_button()
        sleep(2)
        return

    def _purchase_seal_of_solidarity_if_needed(self) -> None:
        try:
            sleep(3)
            seal = self.game_find_template_match(
                "build/seal_of_solidarity.png",
                threshold=0.7,
            )

            if not seal:
                return
            purchase = self.game_find_template_match(
                "build/purchase.png",
                threshold=0.7,
            )

            if not purchase:
                return

            self.tap(Coordinates(*purchase))
            sleep(2)
            purchase_ok = self.game_find_template_match("build/gem_purchase_ok.png")
            if not purchase_ok:
                return
            self.tap(Coordinates(*purchase_ok))
            btn = self.wait_for_template("build/upgrade.png", timeout=10)
            self.tap(Coordinates(*btn))
        except GameTimeoutError:
            return

    def _handle_replenish_all(self, button_template: str) -> None:
        try:
            replenish = self.wait_for_template(
                "gui/replenish_all.png",
                timeout=5,
            )
            self.tap(Coordinates(*replenish))
            btn = self.wait_for_template(button_template, timeout=10)
            self.tap(Coordinates(*btn))
        except GameTimeoutError:
            return
        return

    def _recruit_troops(self) -> None:
        logging.info("Recruiting Troops")
        _ = self.wait_for_template(
            "gui/map.png",
            crop=CropRegions(right=0.8, top=0.8),
            timeout=10,
            threshold=0.7,
        )

        for i in range(5):
            self.tap(Coordinates(80, 610))
            sleep(1)

        while True:
            sleep(1)
            try:
                recruitment_x, recruitment_y = self.wait_for_template(
                    "recruitment/recruit.png",
                    crop=CropRegions(left=0.5, top=0.6),
                    timeout=10,
                )
            except GameTimeoutError:
                return None

            tier_icon_y = 300
            tier_icon_xs = [860, 980, 1120, 1260, 1380]
            if self.get_config().auto_play_config.recruit_troops:
                prev_tier_icon_x = tier_icon_xs[0]
                for i, tier_icon_x in enumerate(tier_icon_xs):
                    if self.recruitment_max_tier - 1 == i:
                        break
                    self.tap(Coordinates(tier_icon_x, tier_icon_y))
                    result = self.find_any_template(
                        templates=[
                            "recruitment/go.png",
                            "recruitment/upgrade.png",
                        ],
                    )
                    if result is None:
                        prev_tier_icon_x = tier_icon_x
                        continue

                    template, x, y = result
                    match template:
                        case "recruitment/go.png":
                            self.recruitment_max_tier = i + 1
                            self.click(Coordinates(prev_tier_icon_x, y))
                            sleep(1)
                            break
                        case "recruitment/upgrade.png":
                            self.click(Coordinates(x, y))
                            sleep(1)
                            break

            self.tap(Coordinates(recruitment_x, recruitment_y))
            self._handle_replenish_all("recruitment/recruit.png")
            sleep(1)
            _ = self.wait_for_template(
                "gui/map.png",
                crop=CropRegions(right=0.8, top=0.8),
                timeout=10,
                threshold=0.7,
            )
            self.tap(Coordinates(80, 610))

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
            game_map = self.game_find_template_match(
                "gui/map.png",
                crop=CropRegions(right=0.8, top=0.6),
                threshold=0.7,
            )
            if not game_map:
                logging.warning("Map not found skipping resource gathering")
                return
            self.tap(Coordinates(*game_map))
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
                    "gathering/troop_max_5.png",
                    "gathering/troop_max_4.png",
                    "gathering/troop_max_3.png",
                    "gathering/troop_max_2.png",
                ],
                crop=CropRegions(left=0.8, bottom=0.5),
                timeout=5,
            )
        except GameTimeoutError:
            return False
        return True

    def _start_gathering(self, search_coordinates: Coordinates) -> None:
        while not self._troops_are_dispatched():
            self.tap(search_coordinates)

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
            logging.info(f"Searching {resource}")
            x, y = self.wait_for_template(node, timeout=10)
            self.tap(Coordinates(x, y))
            _ = self.wait_for_template("gui/search.png", timeout=10)
            sleep(1)
            search_button = self.wait_for_template(
                "gui/search.png",
                threshold=0.7,
                timeout=10,
            )
            self.tap(Coordinates(*search_button))
            sleep(1)
            try:
                self.wait_until_template_disappears(
                    "gui/search.png",
                    threshold=0.7,
                    timeout=5,
                )
            except GameTimeoutError:
                logging.warning(f"{resource} not found, trying next one")
                self.press_back_button()
                self.gather_count += 1
                sleep(1)
                continue
            sleep(4)
            self.tap(Coordinates(960, 520))
            x, y = self.wait_for_template("gui/gather.png", timeout=10)
            sleep(1)
            self.tap(Coordinates(x, y))
            sleep(1)
            template, x, y = self.wait_for_any_template(
                templates=["gui/create_new_troop.png", "gui/march_blue.png"],
                timeout=10,
            )
            if template == "gui/march_blue.png":
                self.press_back_button()
                sleep(1)
                logging.warning("Troops already dispatched cancelling gathering")
                return
            sleep(1)
            self.tap(Coordinates(x, y))
            x, y = self.wait_for_template("gui/march.png", timeout=10)
            sleep(1)
            self.tap(Coordinates(x, y))
            sleep(3)
            self.gather_count += 1
            resource_count = self.gather_count // 4 + 1
            logging.info(f"Gathering {resource} #{resource_count}")
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
        self.tap(Coordinates(1560, 970))
        self.wait_for_template("alliance/alliance_shop.png")
        sleep(2)

        if self.get_config().auto_play_config.alliance_research:
            logging.info("Opening Alliance Research window")
            research = self.game_find_template_match("alliance/research.png")
            if research:
                self.tap(Coordinates(*research))
                self._handle_alliance_research()
            else:
                logging.info("Alliance Research button not found")
        else:
            logging.info("Alliance Research disabled")
        if self.get_config().auto_play_config.alliance_gifts:
            logging.info("Opening Alliance Gifts window")
            gift = self.game_find_template_match("alliance/gift.png")
            if gift:
                self.tap(Coordinates(*gift))
                sleep(2)
                self._handle_alliance_gift()
        else:
            logging.info("Alliance Gifts disabled")
        while x_btn := self.game_find_template_match("gui/x.png"):
            self.tap(Coordinates(*x_btn))
            sleep(2)
        self.last_alliance_research_and_gift = time()
        return

    def _handle_alliance_gift(self) -> None:
        treasure_chest = self.game_find_template_match("alliance/treasure_chest.png")
        if treasure_chest:
            self.tap(Coordinates(*treasure_chest))
            sleep(0.2)
            self.tap(Coordinates(*treasure_chest))
            sleep(6)
            ok = self.game_find_template_match("gui/ok.png")
            if ok:
                self.tap(Coordinates(*ok))
                sleep(1)
        claim_all = self.game_find_template_match("alliance/claim_all.png")
        if claim_all:
            self.tap(Coordinates(*claim_all))
            sleep(2)
        gift_chest = self.game_find_template_match("alliance/gift_chest.png")
        if not gift_chest:
            return
        self.tap(Coordinates(*gift_chest))
        sleep(1)
        while claim := self.game_find_template_match("gui/claim.png"):
            self.tap(Coordinates(*claim))
            sleep(1)
            refresh = self.game_find_template_match("alliance/gift_chest_refresh.png")
            if refresh:
                self.tap(Coordinates(*refresh))
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
                timeout=10,
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
                self.swipe(800, 540, 300, 540)
                sleep(2)
            logging.warning("Recommended research not found, swiping back")
            for _ in range(6):
                self.swipe(300, 540, 800, 540)
                sleep(2)
            return None

        recommended = find_or_swipe_recommended()

        if not recommended:
            logging.warning("No recommended alliance research")
            return
        x, y = recommended
        self.tap(Coordinates(x + 80, y - 150))
        sleep(2)
        donate = self.game_find_template_match(
            "alliance/research_donate.png", crop=CropRegions(left=0.6, top=0.6)
        )
        if donate:
            for i in range(10):
                self.tap(Coordinates(*donate))
                sleep(0.1)
            self._handle_replenish_all("alliance/research_donate.png")
        x_button = self.game_find_template_match("gui/x.png")
        if x_button:
            self.tap(Coordinates(*x_button))
            sleep(1)
        self.press_back_button()
        sleep(1)
        return

    def _click_resources(self) -> None:
        self._center_city_view_on_research_lab()
        logging.info("Clicking resources")
        while result := self.find_any_template(
            [
                "gui/ok.png",
                "harvest/food.png",
                "harvest/wood.png",
                "harvest/stone.png",
                "harvest/gold.png",
                "harvest/food_full.png",
                "harvest/wood_full.png",
                "harvest/stone_full.png",
                "harvest/gold_full.png",
            ],
            threshold=0.7,
            crop=CropRegions(top=0.3, left=0.1, right=0.1, bottom=0.1),
        ):
            _, x, y = result
            self.tap(Coordinates(x, y))
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
            self.tap(Coordinates(x, y))
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
