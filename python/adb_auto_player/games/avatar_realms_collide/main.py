"""Avatar Realms Collide Main Module."""

import datetime
import logging
from collections.abc import Callable
from enum import StrEnum
from time import sleep, time

from adb_auto_player import Coordinates, CropRegions, GameTimeoutError, MatchMode
from adb_auto_player.adb import get_running_app
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


screen_center = Coordinates(1920 // 2, 1080 // 2)
crop_city_bubble = CropRegions(top=0.25, bottom=0.3, left=0.1, right=0.1)
crop_bottom_right_circle = CropRegions(top=0.7, bottom=0.15, left=0.75, right=0.05)
crop_city_map = CropRegions(right=0.8, top=0.8)
coordinates_map = Coordinates(100, 1000)
coordinates_search = Coordinates(80, 820)


class AvatarRealmsCollide(AvatarRealmsCollideBase):
    """Avatar Realms Collide Game."""

    gather_count: int = 0
    last_campaign_collection: float = 0
    last_alliance_research_and_gift: float = 0
    unchecked_hold_position_after_attack: bool = False
    recruitment_max_tier: int = 6
    no_ap: bool = False
    package_name: str = "com.angames.android.google.avatarbendingtheworld"
    utc_datetime: datetime.datetime = datetime.datetime.now(datetime.UTC)
    last_expedition_datetime: datetime.datetime | None = None

    def auto_play(self) -> None:
        """Auto Play."""
        self.start_up(device_streaming=True)
        while True:
            try:
                self._restart_for_daily_reset()
                self._auto_play_loop()
                sleep(5)
            except NoRechargeableAPError:
                logging.error("AP cannot be recharged disabling Expedition")
                self.no_ap = True
            except GameTimeoutError as e:
                logging.error(f"{e}")
                sleep(2)
                logging.info("Restarting Auto Play...")

    def _restart_for_daily_reset(self) -> None:
        """Restart the game when a new day starts.

        Raises:
            GameTimeoutError: Game cannot be restarted.
        """
        today = datetime.datetime.now(datetime.UTC)
        if self.utc_datetime.date() != today.date():
            logging.info("Daily Reset, Restarting Game")
            self._start_game(force_stop=True)
            self.utc_datetime = today

    def _start_game(self, force_stop: bool = False) -> None:
        """Restart the game.

        Raises:
            GameTimeoutError: Game cannot be restarted.
        """
        if force_stop:
            logging.info("Exiting Game...")
            # TODO should be a device function device.close_game(self.package_name)
            self.device.shell(["am", "force-stop", self.package_name])
            sleep(5)

        if get_running_app(self.device) == self.package_name:
            logging.debug("Game already running")
            return

        seconds_since_restart_attempt: int = 0
        max_seconds: int = 90
        while True:
            if seconds_since_restart_attempt > max_seconds:
                raise GameTimeoutError("Could not restart game after 90 seconds.")

            # TODO should be a helper function self.is_game_running()
            if get_running_app(self.device) != self.package_name:
                logging.info("Restarting Game...")
                # TODO should be a device function device.start_game(self.package_name)
                self.device.shell(
                    [
                        "monkey",
                        "-p",
                        self.package_name,
                        "-c",
                        "android.intent.category.LAUNCHER",
                        "1",
                    ]
                )
                sleep(10)
                seconds_since_restart_attempt = 0

            if self._is_inside_city() or self._is_outside_city():
                logging.info("Game started")
                break

            self._check_for_update()
            self.tap(screen_center)
            sleep(3)
            seconds_since_restart_attempt += 3
        return

    def _check_for_update(self) -> None:
        if download_button := self.game_find_template_match(
            "button/download.png",
            threshold=0.7,
        ):
            logging.info("Downloading Update...")
            self.tap(Coordinates(*download_button))
            # TODO if update is bigger should check if update is still downloading

    def _is_inside_city(self) -> bool:
        return (
            self.game_find_template_match(
                "city/map.png",
                crop=crop_city_map,
                threshold=0.8,
            )
            is not None
        )

    def _is_outside_city(self) -> bool:
        return (
            self.game_find_template_match(
                "world/plus_marker.png",
                crop=CropRegions(
                    left=0.5,
                    right=0.4,
                    bottom=0.8,
                ),
                threshold=0.8,
            )
            is not None
        )

    def _close_single_menu_item(self) -> bool:
        result = self.find_any_template(
            templates=[
                "button/cancel.png",
                "button/ok.png",
                "button/x.png",
            ]
        )
        if result:
            template, x, y = result
            self.tap(Coordinates(x, y))
            sleep(2)
            return True
        return False

    def _close_all_menus(self) -> None:
        while self._close_single_menu_item():
            continue

    def _navigate_to_city(self) -> None:
        logging.debug("Navigating to city")
        self._navigate_city_or_outside(inside_city=True)

    def _navigate_city_or_outside(self, inside_city: bool = True) -> None:
        count = 0
        max_attempts = 30
        while True:
            if count >= max_attempts:
                logging.error("Max attempts reached, Restarting Game")
                self._start_game(force_stop=True)
                count = 0
            else:
                self._start_game()
                count += 1

            inside_condition = inside_city and self._is_inside_city()
            outside_condition = not inside_city and self._is_outside_city()
            if inside_condition or outside_condition:
                break

            inside_condition = inside_city and self._is_outside_city()
            outside_condition = not inside_city and self._is_inside_city()
            if inside_condition or outside_condition:
                self.tap(coordinates_map)
                sleep(5)
                continue

            if not self._close_single_menu_item():
                self.press_back_button()
            sleep(3)

    def _navigate_outside_city(self) -> None:
        logging.info("Navigating outside city")
        self._navigate_city_or_outside(inside_city=False)

    def _close_vip_shop_bubble(self):
        self._navigate_to_city()
        count = 0
        max_retry_count = 10
        while vip_shop_bubble := self.game_find_template_match(
            "city/bubble/vip_shop.png",
            crop=crop_city_bubble,
            threshold=0.8,
        ):
            if count > max_retry_count:
                raise GameTimeoutError("Failed to close VIP Shop bubble")
            logging.info("Closing VIP shop bubble")
            self.tap(Coordinates(*vip_shop_bubble))
            sleep(2)
            count += 1

    def _shop_trading_post(self) -> None:
        self._navigate_to_city()
        count = 0
        max_retry_count = 10
        while trading_post_bubble := self.game_find_template_match(
            "city/bubble/trading_post.png",
            crop=crop_city_bubble,
            threshold=0.8,
        ):
            if count > max_retry_count:
                raise GameTimeoutError("Failed to shop in Trading Post")
            logging.info("Opening Trading Post")
            self.tap(Coordinates(*trading_post_bubble))
            sleep(2)
            count += 1

        self._handle_trading_post()

    def _skip_trading_post(self) -> bool:
        config = self.get_config().trading_post
        return not any(
            [
                config.row_1_resources,
                config.row_2_speedups,
                config.row_3_hero_upgrade_items,
                config.row_4_boosts_and_teleports,
            ]
        )

    def _handle_trading_post(self) -> None:
        if not self.game_find_template_match(
            "trading_post/trading_post.png",
            crop=CropRegions(left=0.4, right=0.4, top=0.1, bottom=0.8),
        ):
            return

        if self._skip_trading_post():
            logging.info("Skipping Trading Post because all options are disabled")
            return

        self._purchase_trading_post_round()
        while refresh := self.game_find_template_match("trading_post/free_refresh.png"):
            if self.game_find_template_match("trading_post/legendary_spirit_badge.png"):
                logging.warning("TODO: Legendary Spirit Badge")
                break
            self.click(Coordinates(*refresh))
            sleep(2)
            self._purchase_trading_post_round()
        return

    def _purchase_trading_post_round(
        self,
    ) -> None:
        """Performs a full round of trading post purchases and swipe."""
        crop_top_row = CropRegions(left=0.2, right=0.2, top=0.2, bottom=0.5)
        crop_bottom_row = CropRegions(left=0.2, right=0.2, top=0.5, bottom=0.1)

        if self.get_config().trading_post.row_1_resources:
            self._purchase_trading_post(crop_top_row)

        if self.get_config().trading_post.row_2_speedups:
            self._purchase_trading_post(crop_bottom_row)

        # Swipe to reveal next items
        self.swipe(1615, 870, 1615, 0)
        sleep(2)

        if self.get_config().trading_post.row_3_hero_upgrade_items:
            self._purchase_trading_post(crop_top_row)

        # TODO buy legendary spirit badge?
        # self.game_find_template_match("trading_post/legendary_spirit_badge.png")
        # self.game_find_template_match(
        #   "trading_post/legendary_spirit_badge_80_percent.png"
        # )

        if self.get_config().trading_post.row_4_boosts_and_teleports:
            self._purchase_trading_post(crop_bottom_row)

    def _purchase_trading_post(self, crop: CropRegions) -> None:
        while result := self.find_any_template(
            [
                "trading_post/food.png",
                "trading_post/wood.png",
                "trading_post/stone.png",
            ],
            crop=crop,
        ):
            _, x, y = result
            self.tap(Coordinates(x, y))
            sleep(2)

    def _auto_play_loop(self) -> None:
        def safe_execute(action_func: Callable[[], None]):
            try:
                action_func()
            except GameTimeoutError as e:
                logging.error(f"{e}")
                self._navigate_to_city()

        # Deal with Bubbles
        self._close_vip_shop_bubble()
        self._click_resources()
        self._heal_troops()
        self._shop_trading_post()
        self._click_help_bubbles()

        self._build()
        safe_execute(self._research)
        self._click_help_bubbles()

        safe_execute(self._recruit_troops)

        for action in [
            self._collect_campaign_chest,
            self._use_free_scroll,
            self._alliance_research_and_gift,
        ]:
            safe_execute(action)

        self._expedition()
        self._gather_resources()

    def _recharge_ap(self) -> bool:
        sleep(1)
        go = self.game_find_template_match("expedition/go.png")
        if not go:
            return False
        self.tap(Coordinates(*go))
        use = self.game_find_template_match(
            "expedition/use.png",
            match_mode=MatchMode.TOP_RIGHT,
        )
        if use:
            self.tap(Coordinates(*use))
            sleep(1)
            self._close_single_menu_item()
            return True
        raise NoRechargeableAPError()

    def _uncheck_hold_position_after_attack(self) -> None:
        if (
            self.unchecked_hold_position_after_attack
            or self.get_config().auto_play.skip_hold_position_check
        ):
            return

        logging.info("Unchecking Hold Position after Attack")
        count = 0
        max_attempts = 3
        while count < max_attempts:
            try:
                result = self.wait_for_any_template(
                    [
                        "circle/search1.png",
                        "circle/search2.png",
                        "circle/search3.png",
                        "circle/search4.png",
                    ],
                    crop=CropRegions(right=0.8, top=0.6),
                    timeout=5,
                )
                _, x, y = result
                self.tap(Coordinates(x, y))
                shattered_skulls = self.wait_for_template(
                    "expedition/shattered_skulls.png"
                )
                self.tap(Coordinates(*shattered_skulls))
                while True:
                    search = self.wait_for_template(
                        "button/search.png",
                        timeout=5,
                    )
                    self.tap(Coordinates(*search))
                    sleep(1)
                    self.tap(Coordinates(1920 // 2, 1080 // 2))
                    template, x, y = self.wait_for_any_template(
                        [
                            "expedition/attack.png",
                            "button/ok.png",
                        ],
                        timeout=5,
                    )

                    if template == "button/ok.png":
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

    def _is_expedition_cleared_this_period(self) -> bool:
        if self.last_expedition_datetime:
            last_period = self.last_expedition_datetime.hour // 6
            current_period = datetime.datetime.now(datetime.UTC).hour // 6
            print(f"last_period {last_period}")
            print(f"current_period {current_period}")
            if last_period == current_period:
                return True
        return False

    def _search_expedition(self) -> tuple[str, int, int] | None:
        templates = [
            "expedition/next_refresh.png",
            "expedition/chest/green.png",
            "expedition/chest/blue.png",
            "expedition/chest/purple.png",
            "expedition/chest/orange.png",
            "expedition/chest/orange2.png",
            "expedition/chest/orange3.png",
            "expedition/cave/orange.png",
            # "expedition/scout/orange.png",
            "expedition/troops/orange.png",
            "expedition/cave/purple.png",
            "expedition/scout/purple.png",
            # "expedition/troops/purple.png",
            "expedition/cave/blue.png",
            "expedition/scout/blue.png",
            "expedition/troops/blue.png",
            "expedition/cave/green.png",
            "expedition/scout/green.png",
            "expedition/troops/green.png",
        ]

        now = datetime.datetime.now(datetime.UTC)
        if not self.game_find_template_match("expedition/expedition.png"):
            self.tap(Coordinates(80, 230))
            self.wait_for_template("expedition/expedition.png", timeout=10)

        try:
            template, x, y = self.wait_for_any_template(
                templates=templates,
                threshold=0.7,
                timeout=10,
                timeout_message="No Expeditions found",
            )

            if template == "expedition/next_refresh.png":
                self.last_expedition_datetime = now
                print(f"set {self.last_expedition_datetime}")
                logging.info("Expedition cleared, waiting for next refresh")
                return None
            return template, x, y
        except GameTimeoutError:
            logging.info("No Expeditions found")
            return None

    def _expedition(self) -> None:
        if not self.get_config().auto_play.expedition or self.no_ap:
            logging.info("Expedition disabled")
            return

        if self._is_expedition_cleared_this_period():
            logging.info("Expedition cleared, waiting for next refresh")
            return

        if self._troops_are_dispatched():
            logging.info("All Troops dispatched skipping expedition")
            return

        self._navigate_outside_city()
        logging.info("Checking Expedition")
        self._uncheck_hold_position_after_attack()

        while True:
            if not self._search_expedition():
                return
            sleep(1)

            result = self._search_expedition()
            if result is None:
                return
            template, x, y = result
            max_attempts = 3
            attempt = 0
            while attempt < max_attempts and not self.find_any_template(
                [
                    "button/ok.png",
                    "expedition/go.png",
                ]
            ):
                attempt += 1
                self.tap(Coordinates(x, y))
                sleep(3)

            button_result = self.find_any_template(
                [
                    "button/ok.png",
                    "expedition/go.png",
                ]
            )

            if not button_result:
                raise GameTimeoutError("Could not find ok or go button.")

            template, x, y = button_result

            if template == "button/ok.png":
                sleep(1)
                self.tap(Coordinates(x, y))
                continue

            self.tap(Coordinates(x, y))
            sleep(1)
            timeout_count = 0
            max_timeout_count = 2
            while timeout_count < max_timeout_count:
                self.tap(Coordinates(1920 // 2, 1080 // 2))
                try:
                    if self._handle_expedition():
                        break
                except GameTimeoutError:
                    timeout_count += 1
                    continue
        return

    def _handle_expedition(self) -> bool:
        """Handle Expedition.

        Raises:
            GameTimeoutError
        """
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
                self._handle_cave(Coordinates(x, y))
            case "expedition/survey.png":
                self._handle_survey(Coordinates(x, y))
            case "expedition/murong.png":
                return self._handle_murong()
        return True

    def _handle_cave(self, button_coords: Coordinates) -> None:
        self.tap(button_coords)
        if self._recharge_ap():
            self.tap(button_coords)
        start = self.wait_for_template("expedition/start.png", timeout=10)
        self.tap(Coordinates(*start))
        ok = self.wait_for_template("button/ok.png", timeout=10)
        self.tap(Coordinates(*ok))
        sleep(3)

    def _handle_survey(self, button_coords: Coordinates) -> None:
        self.tap(button_coords)
        if self._recharge_ap():
            self.tap(button_coords)

    def _handle_murong(self) -> bool:
        attack = self.game_find_template_match("expedition/attack.png")
        if not attack:
            return False
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

        logging.info("Waiting 90 seconds")
        sleep(90)  # make sure it is dead
        return True

    def _use_free_scroll(self) -> None:
        if not self.get_config().auto_play.collect_free_scrolls:
            logging.info("Collecting Free Scrolls disabled")
            return

        self._navigate_to_city()
        logging.info("Looking for free Scroll")
        scroll = self.find_any_template(
            [
                "city/bubble/scroll_silver.png",
                "city/bubble/scroll_gold.png",
            ],
            crop=crop_city_bubble,
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
            return
        self.tap(Coordinates(*free))
        ok = self.wait_for_template("altar/ok.png", timeout=15)
        self.tap(Coordinates(*ok))
        sleep(1)

    def _collect_campaign_chest(self) -> None:
        if not self.get_config().auto_play.collect_campaign_chest:
            logging.info("Collecting Campaign Chest disabled")
            return

        self._navigate_to_city()
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
            "button/campaign_claim.png",
            threshold=0.7,
        ):
            self.tap(Coordinates(*claim))
            logging.info("Claimed Campaign Chest")
            sleep(1)
        self.last_campaign_collection = time()
        return

    def _build(self) -> None:
        button_1 = Coordinates(80, 220)
        button_2 = Coordinates(80, 350)

        if self.get_config().auto_play.building_slot_1:
            self._navigate_to_city()
            try:
                logging.info("Checking Build Slot 1")
                self._handle_build_button(button_1)
                self._close_all_menus()
            except GameTimeoutError:
                pass
        else:
            logging.info("Build Slot 1 disabled")
        if self.get_config().auto_play.building_slot_2:
            self._navigate_to_city()
            try:
                logging.info("Checking Build Slot 2")
                self._handle_build_button(button_2)
                self._close_all_menus()
            except GameTimeoutError:
                pass
        else:
            logging.info("Build Slot 2 disabled")

    def _handle_build_button(self, button_coordinates: Coordinates) -> None:
        self.tap(button_coordinates)
        sleep(1)
        self.tap(button_coordinates)
        sleep(1)
        _, x, y = self.wait_for_any_template(
            templates=[
                "city/octagon/double_arrow_button.png",
                "city/octagon/double_arrow_button2.png",
            ],
            threshold=0.7,
            crop=crop_city_bubble,
            timeout=10,
        )
        self.tap(Coordinates(x, y))
        while upgrade := self.wait_for_template("button/upgrade.png", timeout=10):
            logging.info("Upgrading Building")
            self.tap(Coordinates(*upgrade))
            self._handle_replenish_all("button/upgrade.png")
            if self.get_config().auto_play.purchase_seal_of_solidarity:
                self._purchase_seal_of_solidarity_if_needed()
        while x_btn := self.game_find_template_match("button/x.png"):
            self.tap(Coordinates(*x_btn))
            sleep(2)

    def _open_research_lab_window_if_ready(self):
        self.tap(Coordinates(80, 480))
        sleep(1)
        self.tap(Coordinates(80, 480))
        sleep(1)

    def _select_military_or_economy_research(self) -> None:
        """Select Research Category.

        Raises:
            GameTimeoutError: Research Window not found.
        """
        template, x, y = self.wait_for_any_template(
            templates=[
                "research/military.png",
                "research/economy.png",
            ],
            timeout=10,
        )
        sleep(2)

        if self.get_config().auto_play.military_first:
            logging.info("Checking Military Research first")
            if template == "research/military.png":
                self.tap(Coordinates(x, y))
                sleep(3)
        elif template == "research/economy.png":
            logging.info("Checking Economy Research first")
            self.tap(Coordinates(x, y))
            sleep(3)

    def _try_to_start_research(self) -> None:
        def click_and_hope_research_pops_up() -> tuple[int, int] | None:
            y_coords = [250, 450, 550, 650, 850]
            for y_coord in y_coords:
                self.tap(Coordinates(1250, y_coord))
                sleep(2)
                result = self.game_find_template_match("research/research.png")
                if result:
                    return result

                x_btn = self.game_find_template_match(
                    "button/x.png", crop=CropRegions(right=0.1)
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
            if self.get_config().auto_play.military_first:
                template = "research/economy.png"

            btn = self.game_find_template_match(template)
            if not btn:
                return None

            self.tap(Coordinates(*btn))
            sleep(1)
            research = try_to_find_research()

        if research:
            self.tap(Coordinates(*research))
            self._handle_replenish_all("research/research.png")
        else:
            logging.error("No research found")
        return None

    def _research(self) -> None:
        if not self.get_config().auto_play.research:
            logging.info("Research disabled")
            return None

        self._navigate_to_city()
        logging.info("Checking Research")
        self._open_research_lab_window_if_ready()

        try:
            self._select_military_or_economy_research()
        except GameTimeoutError:
            return None

        self._try_to_start_research()
        self._close_all_menus()
        return None

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
                "button/purchase.png",
                threshold=0.7,
            )

            if not purchase:
                return

            self.tap(Coordinates(*purchase))
            sleep(2)
            purchase_ok = self.game_find_template_match("button/gem_purchase_ok.png")
            if not purchase_ok:
                return
            self.tap(Coordinates(*purchase_ok))
            btn = self.wait_for_template("button/upgrade.png", timeout=10)
            self.tap(Coordinates(*btn))
        except GameTimeoutError:
            return

    def _handle_replenish_all(self, button_template: str) -> None:
        try:
            replenish = self.wait_for_template(
                "button/replenish_all.png",
                timeout=5,
            )
            self.tap(Coordinates(*replenish))
            btn = self.wait_for_template(button_template, timeout=10)
            self.tap(Coordinates(*btn))
        except GameTimeoutError:
            return
        return

    def _collect_troops(self) -> None:
        for i in range(5):
            self.tap(Coordinates(80, 610))
            sleep(1)

    def _handle_upgrade_troops(self) -> None:
        tier_icon_y = 300
        tier_icon_xs = [860, 980, 1120, 1260, 1380]
        prev_tier_icon_x = tier_icon_xs[0]
        for i, tier_icon_x in enumerate(tier_icon_xs):
            if self.recruitment_max_tier - 1 == i:
                break
            self.tap(Coordinates(tier_icon_x, tier_icon_y))
            sleep(1)
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
                    self.tap(Coordinates(prev_tier_icon_x, y))
                    sleep(1)
                    break
                case "recruitment/upgrade.png":
                    self.tap(Coordinates(x, y))
                    sleep(1)
                    break

    def _recruit_troops(self) -> None:
        if not self.get_config().auto_play.recruit_troops:
            logging.info("Recruiting Troops disabled")
            return None

        self._navigate_to_city()
        logging.info("Recruiting Troops")

        self._collect_troops()

        while True:
            self.tap(Coordinates(80, 610))
            sleep(2)
            try:
                recruitment_x, recruitment_y = self.wait_for_template(
                    "recruitment/recruit.png",
                    crop=CropRegions(left=0.5, top=0.6),
                    timeout=10,
                )
            except GameTimeoutError:
                break

            if self.get_config().auto_play.upgrade_troops:
                self._handle_upgrade_troops()

            self.tap(Coordinates(recruitment_x, recruitment_y))
            self._handle_replenish_all("recruitment/recruit.png")
            sleep(1)
            self._close_all_menus()
        self._close_all_menus()
        return None

    def _gather_resources(self) -> None:
        if not self.get_config().auto_play.gather_resources:
            logging.info("Gathering Resources disabled")
            return

        if self._troops_are_dispatched():
            logging.info("All Troops dispatched skipping resource gathering")
            return

        self._navigate_outside_city()
        logging.info("Gathering Resources")
        self._start_gathering()

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

    def _start_gathering(self) -> None:
        while not self._troops_are_dispatched():
            self.tap(coordinates_search)

            nodes = {
                "Food": "gathering/farmland.png",
                "Wood": "gathering/logging_area.png",
                "Stone": "gathering/mining_site.png",
                "Gold": "gathering/gold_mine.png",
            }
            resources: list[ResourceEnum] = self.get_config().auto_play.gather_resources

            resource = resources[self.gather_count % len(resources)]
            node = nodes[resource]
            logging.info(f"Searching {resource}")
            x, y = self.wait_for_template(node, timeout=10)
            self.tap(Coordinates(x, y))
            _ = self.wait_for_template("button/search.png", timeout=10)
            sleep(1)
            search_button = self.wait_for_template(
                "button/search.png",
                threshold=0.7,
                timeout=10,
            )
            self.tap(Coordinates(*search_button))
            sleep(1)
            try:
                self.wait_until_template_disappears(
                    "button/search.png",
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
            x, y = self.wait_for_template("button/gather.png", timeout=10)
            sleep(1)
            self.tap(Coordinates(x, y))
            sleep(1)
            template, x, y = self.wait_for_any_template(
                templates=["button/create_new_troop.png", "button/march_blue.png"],
                timeout=10,
            )
            if template == "button/march_blue.png":
                self.press_back_button()
                sleep(1)
                logging.warning("Troops already dispatched cancelling gathering")
                return
            sleep(1)
            self.tap(Coordinates(x, y))
            x, y = self.wait_for_template("button/march.png", timeout=10)
            sleep(1)
            self.tap(Coordinates(x, y))
            sleep(3)
            self.gather_count += 1
            resource_count = self.gather_count // len(resources) + 1
            logging.info(f"Gathering {resource} #{resource_count}")
        return

    def _alliance_research_and_gift(self) -> None:
        if (
            not self.get_config().auto_play.alliance_research
            and not self.get_config().auto_play.alliance_gifts
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

        self._navigate_to_city()
        logging.info("Opening Alliance window")
        if not self.game_find_template_match("city/map.png", crop=crop_city_map):
            logging.warning("Map not found skipping alliance research and gift")
            return
        self.tap(Coordinates(1560, 970))
        self.wait_for_template("alliance/alliance_shop.png")
        sleep(2)

        if self.get_config().auto_play.alliance_research:
            logging.info("Opening Alliance Research window")
            research = self.game_find_template_match("alliance/research.png")
            if research:
                self.tap(Coordinates(*research))
                self._handle_alliance_research()
            else:
                logging.info("Alliance Research button not found")
        else:
            logging.info("Alliance Research disabled")
        if self.get_config().auto_play.alliance_gifts:
            logging.info("Opening Alliance Gifts window")
            gift = self.game_find_template_match("alliance/gift.png")
            if gift:
                self.tap(Coordinates(*gift))
                sleep(2)
                self._handle_alliance_gift()
        else:
            logging.info("Alliance Gifts disabled")
        while x_btn := self.game_find_template_match("button/x.png"):
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
            ok = self.game_find_template_match("button/ok.png")
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
        while claim := self.game_find_template_match("button/claim.png"):
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
                    crop=CropRegions(left=0.2, right=0.2, top=0.1),
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
        x_button = self.game_find_template_match("button/x.png")
        if x_button:
            self.tap(Coordinates(*x_button))
            sleep(1)
        self.press_back_button()
        sleep(1)
        return

    def _click_resources(self) -> None:
        self._navigate_to_city()
        logging.info("Clicking resources")
        count = 0
        max_retry_count = 10
        while result := self.find_any_template(
            [
                "city/bubble/food.png",
                "city/bubble/wood.png",
                "city/bubble/stone.png",
                "city/bubble/gold.png",
                "city/bubble/food_full.png",
                "city/bubble/wood_full.png",
                "city/bubble/stone_full.png",
                "city/bubble/gold_full.png",
            ],
            threshold=0.7,
            crop=crop_city_bubble,
        ):
            if count > max_retry_count:
                raise GameTimeoutError("Failed to click resource bubbles")
            _, x, y = result
            self.tap(Coordinates(x, y))
            sleep(1)
            count += 1

    def _click_help_bubbles(self) -> None:
        self._navigate_to_city()
        logging.info("Clicking help")
        no_help_found_count = 0
        max_count = 3
        while no_help_found_count < max_count:
            result = self.find_any_template(
                [
                    "city/bubble/help.png",
                    "city/bubble/help_request.png",
                ],
                threshold=0.7,
                crop=crop_city_bubble,
            )

            if not result:
                result = self.find_any_template(
                    [
                        "circle/help1.png",
                        "circle/help2.png",
                        "circle/help3.png",
                        "circle/help4.png",
                        "circle/help5.png",
                    ],
                    threshold=0.7,
                    crop=crop_bottom_right_circle,
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

    def _collect_healed_troops(self) -> None:
        if bubble := self.game_find_template_match("city/bubble/healing_complete.png"):
            logging.info("Collected healed troops")
            self.tap(Coordinates(*bubble))
            sleep(3)

    def _heal_troops(self) -> None:
        self._collect_healed_troops()

        bandage = self.game_find_template_match("city/bubble/bandage.png")
        if not bandage:
            return

        logging.warning("Healing Troops not implemented.")
        # self.tap(Coordinates(*bandage))
        # self._handle_heal_troops()

    def _handle_heal_troops(self) -> None:
        try:
            # heal = self.wait_for_template("button/heal.png", timeout=10)
            pass
        except GameTimeoutError:
            return
        # TODO
        # lower all healing to 0
        # heal 330 troops changeable in config
