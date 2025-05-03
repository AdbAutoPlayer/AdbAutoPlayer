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
                "world.png",
                crop=crop_bottom_menu,
            )
            is not None
        )

    def _is_outside_town(self) -> bool:
        return (
            self.game_find_template_match(
                "town.png",
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
                "town.png",
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
                "world.png",
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
            logging.info("Info view already open")
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

            if self._is_info_closed():
                if info_button := self.game_find_template_match("info/open_arrow.png"):
                    self.tap(Coordinates(*info_button))
                    sleep(3)
        return

    def _close_info(self) -> None:
        if info_button := self.game_find_template_match("info/close_arrow.png"):
            self.tap(Coordinates(*info_button))
            sleep(3)

    def _auto_play_loop(self) -> None:
        self._click_alliance_help()
        self._gather_resources()
        try:
            self._alliance_tech_contribute()
        except GameTimeoutError as e:
            logging.error(f"{e}")

    def _gather_resources(self) -> None:
        def _is_march_available() -> bool:
            self._navigate_outside_town()
            self._open_info(town=False)
            resource_icons = [
                "info/bread.png",
                "info/wood.png",
                "info/stone.png",
                "info/iron.png",
            ]
            march_icons = ["info/flag.png", "info/march_returning.png"]
            all_icons = march_icons + resource_icons
            march_count = sum(
                len(self.find_all_template_matches(icon, crop=crop_info_left_icons))
                for icon in all_icons
            )
            returns = self.find_all_template_matches(
                "info/return.png",
                crop=crop_info_right_icons,
            )
            return march_count > len(returns)

        if not _is_march_available():
            logging.info("No march available - skipping resource gathering")
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
            self.swipe(1000, 1400, 500, 1400)
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

    def _alliance_tech_contribute(self) -> None:
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
