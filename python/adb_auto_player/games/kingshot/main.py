"""KingShot."""

import datetime
import logging
from enum import StrEnum
from time import sleep

from adb_auto_player import Command, Coordinates, CropRegions, Game, GameTimeoutError
from adb_auto_player.games.kingshot.config import Config
from adb_auto_player.ipc import GameGUIOptions, MenuOption

screen_center = Coordinates(1080 // 2, 1920 // 2)
crop_info_box = CropRegions(
    right=0.35,
    top=0.2,
    bottom=0.3,
)
crop_info_left_icons = CropRegions(
    right=0.8,
    top=0.2,
    bottom=0.3,
)
crop_info_right_icons = CropRegions(
    left=0.5,
    right=0.35,
    top=0.2,
    bottom=0.3,
)
crop_marching_window_returns = CropRegions(
    left=0.2,
    right=0.6,
    top=0.15,
    bottom=0.5,
)
crop_bottom_menu = CropRegions(top=0.9)


class ModeCategory(StrEnum):
    """Enumeration for mode categories used in the GUIs accordion menu."""

    ALL = "All"


class KingShot(Game):
    """KingShot."""

    gathering_count = 0
    next_alliance_tech_contribution_at = datetime.datetime.now(datetime.UTC)
    next_claim_conquest_at = datetime.datetime.now(datetime.UTC)

    def __init__(self) -> None:
        """Initialize KingShot."""
        super().__init__()
        self.supported_resolutions = [
            "1080x1920",
        ]
        self.package_name_substrings = [
            "com.run.tower.defense",
        ]

    def _start_up(self, device_streaming: bool = False) -> None:
        """Give the bot eyes."""
        if self.device is None:
            logging.debug("start_up")
            self.open_eyes(device_streaming=device_streaming)

    def _restart_game(self) -> None:
        logging.info("Restarting game")
        self.force_stop_game()
        sleep(5)

        seconds_since_restart_attempt: int = 0
        max_seconds: int = 90
        while True:
            if seconds_since_restart_attempt > max_seconds:
                raise GameTimeoutError("Could not restart game after 90 seconds.")

            if not self.is_game_running():
                logging.info("Restarting game...")
                self.start_game()
                sleep(10)
                seconds_since_restart_attempt = 0

            if self._is_inside_town() or self._is_outside_town():
                logging.info("Game started")
                break

            self.tap(screen_center)
            sleep(3)
            seconds_since_restart_attempt += 3

    def _is_inside_town(self) -> bool:
        return (
            self.game_find_template_match(
                "bottom_menu/world.png",
                crop=crop_bottom_menu,
            )
            is not None
        )

    def _is_outside_town(self) -> bool:
        return (
            self.game_find_template_match(
                "bottom_menu/town.png",
                crop=crop_bottom_menu,
            )
            is not None
        )

    def _is_info_closed(self) -> bool:
        return (
            self.game_find_template_match(
                "info/open_arrow.png", crop=CropRegions(right=0.8, top=0.3, bottom=0.3)
            )
            is not None
        )

    def _is_info_open(self) -> bool:
        return (
            self.game_find_template_match(
                "info/close_arrow.png", crop=CropRegions(left=0.5, top=0.3, bottom=0.3)
            )
            is not None
        )

    def auto_play(self) -> None:
        """AutoPlay."""
        self._start_up(device_streaming=True)
        while True:
            try:
                self._auto_play_loop()
                sleep(5)
            except Exception as e:
                logging.error(f"{e}")
                self._restart_game()

    def _navigate_to_town(self) -> None:
        while True:
            if not self.is_game_running():
                self._restart_game()
            if self._is_inside_town():
                break

            if town := self.game_find_template_match(
                "bottom_menu/town.png",
                crop=crop_bottom_menu,
            ):
                self.tap(Coordinates(*town))
                sleep(3)
                continue

            self.press_back_button()
            sleep(3)

    def _navigate_outside_town(self) -> None:
        while True:
            if self._is_outside_town():
                break
            self._navigate_to_town()
            if world := self.game_find_template_match(
                "bottom_menu/world.png",
                crop=crop_bottom_menu,
            ):
                self.tap(Coordinates(*world))
                sleep(3)

    def _open_info(self, town: bool = True) -> None:
        def info_open_and_tab_switched() -> bool:
            if self._is_info_open():
                if town:
                    self.tap(Coordinates(200, 400))  # Town
                else:
                    self.tap(Coordinates(500, 400))  # Wilderness
                sleep(0.5)
                return True
            return False

        if info_open_and_tab_switched():
            logging.debug("Info view already open")
            return

        logging.info("Opening Info view")
        while True:
            if not self.is_game_running():
                raise Exception("Game crashed")

            if info_open_and_tab_switched():
                break

            returns = self.find_all_template_matches(
                "marching/return.png",
                crop=crop_marching_window_returns,
            )
            minimized_marching_window_return_count = 2
            if len(returns) > minimized_marching_window_return_count:
                self.tap(Coordinates(40, 320))  # minimize Marching window
                sleep(0.5)
                continue

            if self._is_info_closed():
                if info_button := self.game_find_template_match("info/open_arrow.png"):
                    self.tap(Coordinates(*info_button))
                    sleep(3)
                    continue
            self.press_back_button()
            sleep(1)
        return

    def _close_info(self) -> None:
        if info_button := self.game_find_template_match("info/close_arrow.png"):
            self.tap(Coordinates(*info_button))
            sleep(3)

    def _auto_play_loop(self) -> None:
        self._click_alliance_help()
        self._collect_online_rewards()
        try:
            self._claim_conquest()
        except GameTimeoutError as e:
            logging.warning(f"{e}")
        self._handle_troops_completed()
        self._handle_info_actions()

        try:
            self._alliance_tech_contribute()
        except GameTimeoutError as e:
            logging.warning(f"{e}")

        try:
            self._gather_resources()
        except GameTimeoutError as e:
            logging.warning(f"{e}")

    def _collect_online_rewards(self) -> None:
        self._open_info(town=True)
        self.swipe_up(sy=1150)
        sleep(1)
        check_mark = self.game_find_template_match(
            "info/check_mark.png",
            crop=CropRegions(left=0.5, right=0.35, top=0.5, bottom=0.3),
        )
        if check_mark:
            logging.info("Collecting Online Rewards")
            self.tap(Coordinates(*check_mark))
            sleep(2)
            self.tap(Coordinates(*check_mark))
            sleep(2)

    def _handle_troops_completed(self) -> None:
        self._navigate_to_town()
        self._open_info(town=True)
        troops_completed = self.find_all_template_matches(
            "info/check_mark.png",
            crop=crop_info_right_icons,
        )

        if troops_completed:
            logging.info("Collecting completed Troops")
        for button in troops_completed:
            self.tap(Coordinates(*button))
            sleep(3)
            self.tap(Coordinates(540, 650))
            sleep(1)
            self._open_info(town=True)
            sleep(1)

    def _handle_info_actions(self) -> None:
        self._navigate_to_town()
        self._open_info(town=True)
        actions = self.find_all_template_matches(
            "info/action.png",
            crop=crop_info_right_icons,
        )

        for action in actions:
            self._navigate_to_town()
            self._open_info(town=True)
            sleep(1)
            self.tap(Coordinates(*action))
            sleep(3)
            if not self._tap_finger():
                return
            if self._handle_building_upgrade():
                continue
            if self._handle_research():
                continue
            if self._handle_training():
                continue
        return

    def _handle_research(self) -> bool:
        if not self.game_find_template_match("research/back.png"):
            return False
        logging.warning("Research not implemented")
        return True

    def _handle_training(self) -> bool:
        if not self.game_find_template_match("training/back.png"):
            return False
        if upgrade_left := self.game_find_template_match("training/upgrade_left.png"):
            self.tap(Coordinates(*upgrade_left))
            sleep(2)
        if upgrade := self.game_find_template_match("training/upgrade.png"):
            self.tap(Coordinates(*upgrade))
            sleep(2)
        if promotion := self.game_find_template_match("training/promotion.png"):
            self.tap(Coordinates(*promotion))
            sleep(1)
            return True
        self.tap(Coordinates(800, 1800))
        sleep(1)
        return True

    def _tap_finger(self) -> bool:
        try:
            _, x, y = self.wait_for_any_template(
                templates=[
                    "finger/1.png",
                    "finger/2.png",
                ],
                crop=CropRegions(top=0.3, bottom=0.3),
                timeout=5,
                delay=0.25,
            )
            self.tap(Coordinates(x, y))
            sleep(2)
            return True
        except GameTimeoutError:
            return False

    def _handle_building_upgrade(self) -> bool:
        if upgrade := self.game_find_template_match("building/upgrade.png"):
            self.tap(Coordinates(*upgrade))
            sleep(1)
            try:
                help_request = self.wait_for_template(
                    "help_request.png",
                    timeout=10,
                    crop=CropRegions(left=0.35, right=0.35, top=0.3, bottom=0.5),
                )
                self.tap(Coordinates(*help_request))
            except GameTimeoutError:
                logging.warning(
                    "Not able to find and click help request for building upgrade"
                )
            return True
        return False

    def _gather_resources(self) -> None:
        def _is_march_available() -> bool:
            self._navigate_outside_town()
            self._open_info(town=False)

            gathering_march_count = sum(
                len(self.find_all_template_matches(icon, crop=crop_info_left_icons))
                for icon in [
                    "info/bread.png",
                    "info/wood.png",
                    "info/stone.png",
                    "info/iron.png",
                ]
            )

            other_march_count = sum(
                len(self.find_all_template_matches(icon, crop=crop_info_left_icons))
                for icon in [
                    "info/flag.png",
                    "info/march_returning.png",
                    "info/attacking.png",
                    "info/returning.png",
                ]
            )

            returns = self.find_all_template_matches(
                "info/return.png",
                crop=crop_info_right_icons,
            )

            available_marches = gathering_march_count + other_march_count - len(returns)
            auto_join_march_puffer = 2

            if self.get_config().auto_play.auto_join:  # Auto-Join
                if (
                    available_marches < auto_join_march_puffer
                    and not self.game_find_template_match("info/attacking.png")
                ):
                    return False

            return available_marches >= 1

        if not _is_march_available():
            if self.get_config().auto_play.auto_join:
                logging.info(
                    "No march available for gathering - keeping one for Auto-Join"
                )
            else:
                logging.info("No march available for gathering")
            return

        logging.info("Gathering resources")

        gathering_nodes = [
            "gathering/bread.png",
            "gathering/wood.png",
            "gathering/stone.png",
            "gathering/iron.png",
        ]

        while _is_march_available():
            self._close_info()
            self.tap(Coordinates(60, 1300))
            sleep(3)
            search = self.wait_for_template("search.png", timeout=3)
            self.swipe_left(y=1400, sx=1000, ex=500)
            node_template = gathering_nodes[self.gathering_count % len(gathering_nodes)]
            node = self.wait_for_template(node_template, timeout=3)
            logging.info(f"Gathering {node_template}")
            self.tap(Coordinates(*node))
            sleep(0.5)
            self.tap(Coordinates(*search))
            gather = self.wait_for_template("gathering/gather.png", timeout=10)
            self.tap(Coordinates(*gather))
            sleep(3)
            while minus := self.game_find_template_match(
                "minus.png",
                crop=CropRegions(left=0.5, bottom=0.5),
            ):
                self.tap(Coordinates(*minus))
            deploy = self.wait_for_template("deploy.png", timeout=3)
            self.tap(Coordinates(*deploy))
            sleep(2)
            self.gathering_count += 1
        return

    def _click_alliance_help(self) -> None:
        logging.info("Clicking Alliance help")
        if alliance_help := self.game_find_template_match(
            "alliance/help.png",
            crop=CropRegions(left=0.5, top=0.8),
        ):
            self.tap(Coordinates(*alliance_help))
            sleep(0.5)

        if chat := self.game_find_template_match(
            "chat.png",
            crop=CropRegions(
                right=0.6,
                bottom=0.8,
            ),
        ):
            self.tap(Coordinates(*chat))
            sleep(0.5)

    def _alliance_tech_contribute(self) -> None:
        self._navigate_to_town()
        now = datetime.datetime.now(datetime.UTC)
        if now < self.next_alliance_tech_contribution_at:
            delta = self.next_alliance_tech_contribution_at - now
            hours, remainder = divmod(delta.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            logging.info(
                "Skipping Alliance Tech contribution, "
                f"next contribution in {int(hours)} hours and {int(minutes)} minutes"
            )
            return
        logging.info("Contributing to Alliance Tech")
        if menu_button := self.game_find_template_match("alliance/menu_button.png"):
            self.tap(Coordinates(*menu_button))
        tech = self.wait_for_template("alliance/tech.png", timeout=5)
        self.tap(Coordinates(*tech))
        recommended_tech = self.wait_for_template(
            "alliance/recommended_tech.png",
            timeout=3,
        )
        self.tap(Coordinates(*recommended_tech))
        try:
            while contribute := self.wait_for_template(
                "alliance/contribute.png",
                timeout=3,
                crop=CropRegions(left=0.5, top=0.5),
            ):
                self.tap(Coordinates(*contribute), blocking=False)
        except GameTimeoutError:
            self.next_alliance_tech_contribution_at = now + datetime.timedelta(hours=1)
        return

    def get_cli_menu_commands(self) -> list[Command]:
        """Required method to return the CLI menu commands."""
        return [
            Command(
                name="KingShotAutoPlay",
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
            game_title="KingShot",
            config_path="kingshot/KingShot.toml",
            menu_options=self._get_menu_options_from_cli_menu(),
            categories=[ModeCategory.ALL],
            constraints=Config.get_constraints(),
        )

    def _load_config(self) -> Config:
        """Load config TOML."""
        self.config = Config.from_toml(self._get_config_file_path())
        return self.config

    def get_config(self) -> Config:
        """Get config."""
        if self.config is None:
            return self._load_config()

        return self.config

    def _claim_conquest(self) -> None:
        now = datetime.datetime.now(datetime.UTC)
        if now < self.next_alliance_tech_contribution_at:
            delta = self.next_alliance_tech_contribution_at - now
            hours, remainder = divmod(delta.total_seconds(), 3600)
            minutes, _ = divmod(remainder, 60)
            logging.info(
                "Skipping Conquest treasure chest, "
                f"next claim in {int(hours)} hours and {int(minutes)} minutes"
            )
            return
        logging.info("Claiming Conquest treasure chest")
        self._navigate_to_town()
        conquest = self.wait_for_template("bottom_menu/conquest.png", timeout=5)
        self.tap(Coordinates(*conquest))

        self.wait_for_template("conquest/conquer.png", timeout=5)
        sleep(1)
        claim = self.game_find_template_match(
            "conquest/claim_chest.png",
            threshold=0.95,
        )
        if not claim:
            logging.info("Conquest treasure chest not ready")
            return
        self.tap(Coordinates(*claim))
        sleep(1)
        claim = self.wait_for_template("conquest/claim_menu.png", timeout=5)
        self.tap(Coordinates(*claim))
        sleep(1)
        self.tap(Coordinates(*claim))
