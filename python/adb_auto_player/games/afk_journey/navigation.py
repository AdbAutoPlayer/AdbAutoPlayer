import logging
from abc import ABC
from enum import StrEnum, auto
from time import sleep

from adb_auto_player.exceptions import (
    AutoPlayerError,
    GameActionFailedError,
    GameNotRunningOrFrozenError,
    GameTimeoutError,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Offset, Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import TemplateMatchResult

from .popup_message_handler import PopupMessageHandler


class Overview(StrEnum):
    """Top-level game view showing your character with menu at the bottom."""

    WORLD = auto()
    HOMESTEAD = auto()
    CURRENT = auto()  # whichever overview you end up in


class Navigation(PopupMessageHandler, ABC):
    # Timeouts
    NAVIGATION_TIMEOUT = 10.0

    # Points (these are the same for World and Homestead overview)
    CENTER_POINT = Point(x=1080 // 2, y=1920 // 2)
    RESONATING_HALL_POINT = Point(x=620, y=1830)
    BATTLE_MODES_POINT = Point(x=460, y=1830)

    def navigate_to_world(self) -> None:
        """Navigate to world view. Previously default_state.

        This is outside of homestead when your character is on the map.
        With buttons: "Mystical House", "Battle Modes", ... visible.
        """
        self._navigate_to_overview(destination=Overview.WORLD)

    def navigate_to_homestead(self):
        self._navigate_to_overview(destination=Overview.HOMESTEAD)

    def navigate_to_current_overview(self) -> Overview:
        return self._navigate_to_overview(destination=Overview.CURRENT)

    def _navigate_to_overview(self, destination: Overview = Overview.WORLD) -> Overview:
        max_attempts = 40
        restart_attempts = 20
        attempts = 0

        restart_attempted = False

        while True:
            if not self.is_game_running():
                logging.error("Game not running.")
                self._handle_restart(Navigation._get_overview_navigation_templates())
            elif attempts >= restart_attempts and not restart_attempted:
                logging.warning("Failed to navigate to default state.")
                self._handle_restart(Navigation._get_overview_navigation_templates())
                restart_attempted = True
            elif attempts >= max_attempts:
                raise GameNotRunningOrFrozenError(
                    "Failed to navigate to default state."
                )
            attempts += 1

            overview = self._handle_overview_navigation(destination)
            if overview is not None:
                break

        if attempts > 1:
            sleep(2)
        return overview

    @staticmethod
    def _get_overview_navigation_templates() -> list[str]:
        return [
            "navigation/homestead/leave.png",
            "navigation/homestead/homestead_enter.png",
            "navigation/homestead/world.png",
            "popup/quick_purchase.png",
            "navigation/confirm.png",
            "navigation/notice.png",
            "navigation/confirm_text.png",
            "navigation/time_of_day.png",
            "navigation/dotdotdot.png",
            "battle/copy.png",
            "guide/close.png",
            "guide/next.png",
            "login/claim.png",
            "arcane_labyrinth/back_arrow.png",
            "battle/exit_door.png",
            "arcane_labyrinth/select_a_crest.png",
            "navigation/resonating_hall_back.png",
        ]

    def _handle_overview_navigation(
        self, overview: Overview = Overview.WORLD
    ) -> Overview | None:
        result = self.find_any_template(Navigation._get_overview_navigation_templates())

        if result is None:
            self.press_back_button()
            sleep(3)
            return None

        match result.template:
            case "navigation/homestead/homestead_enter.png":
                return self._handle_homestead_enter(result, overview)
            case "navigation/homestead/world.png":
                return self._handle_homestead_world(result, overview)
            case "navigation/time_of_day.png":
                return Overview.WORLD
            case "navigation/notice.png":
                # This is the Game Entry Screen
                self.tap(self.CENTER_POINT, scale=True)
                sleep(3)
            case "navigation/confirm.png":
                self._handle_navigation_confirm(result)
            case "navigation/dotdotdot.png" | "popup/quick_purchase.png":
                self.press_back_button()
                sleep(1)
            case "arcane_labyrinth/select_a_crest.png":
                self.tap(Point(550, 1460))  # bottom crest
                sleep(1)
                self.tap(result)
                sleep(1)
            case _:
                self.tap(result)
                sleep(2)
        return None

    def _handle_homestead_world(
        self,
        result: TemplateMatchResult,
        overview: Overview,
    ) -> Overview | None:
        if overview != Overview.WORLD:
            return Overview.HOMESTEAD
        self.tap(result)
        sleep(1)
        return None

    def _handle_homestead_enter(
        self,
        result: TemplateMatchResult,
        overview: Overview,
    ) -> Overview | None:
        if overview != Overview.HOMESTEAD:
            return Overview.WORLD
        self.tap(result)
        sleep(1)
        return None

    def _handle_navigation_confirm(self, result: TemplateMatchResult) -> None:
        if not self.handle_popup_messages():
            self.tap(result)
            sleep(1)

    def _handle_restart(self, templates: list[str]) -> None:
        logging.warning("Trying to restart AFK Journey.")
        self.force_stop_game()
        self.start_game()
        # if your game needs more than 6 minutes to start there is no helping yourself
        max_attempts = 120
        attempts = 0
        while not self.find_any_template(templates) and self.is_game_running():
            if attempts >= max_attempts:
                raise GameNotRunningOrFrozenError(
                    "Failed to navigate to default state."
                )
            attempts += 1
            self.tap(self.CENTER_POINT, scale=True)
            sleep(3)
        sleep(1)

    def navigate_to_resonating_hall(self) -> None:
        def i_am_in_resonating_hall() -> bool:
            try:
                _ = self.wait_for_any_template(
                    templates=[
                        "resonating_hall/artifacts.png",
                        "resonating_hall/collections.png",
                        "resonating_hall/equipment.png",
                    ],
                    timeout=1,
                )
                return True
            except GameTimeoutError:
                return False

        if i_am_in_resonating_hall():
            logging.info("Already in Resonating Hall.")
            return

        logging.info("Navigating to the Resonating Hall.")
        if shortcut := self.game_find_template_match(
            template="navigation/resonating_hall_shortcut",
            crop_regions=CropRegions(top="80%", left="30%", right="30%"),
            threshold=ConfidenceValue("75%"),
        ):
            self.tap(shortcut)
            sleep(3)
            if i_am_in_resonating_hall():
                return

        self.navigate_to_current_overview()
        max_click_count = 3
        click_count = 0

        count = 0
        max_count = 3
        last_error: AutoPlayerError | None = None
        while True:
            count += 1
            if count > max_count:
                if last_error is not None:
                    raise last_error
                raise AutoPlayerError("Failed to navigate to Resonating Hall.")
            try:
                while self._is_in_overview():
                    self.tap(self.RESONATING_HALL_POINT, scale=True)
                    sleep(3)
                    click_count += 1
                    if click_count > max_click_count:
                        raise GameActionFailedError(
                            "Failed to navigate to the Resonating Hall."
                        )
                _ = self.wait_for_any_template(
                    templates=[
                        "resonating_hall/artifacts.png",
                        "resonating_hall/collections.png",
                        "resonating_hall/equipment.png",
                    ],
                    timeout=self.NAVIGATION_TIMEOUT,
                )
                break
            except AutoPlayerError as e:
                logging.warning(e)
                last_error = e
        sleep(1)
        return

    def _is_in_overview(self) -> bool:
        return (
            self.find_any_template(
                templates=[
                    "navigation/homestead/homestead_enter.png",
                    "navigation/homestead/world.png",
                    "navigation/time_of_day.png",
                ],
                crop_regions=CropRegions(left=0.6, bottom=0.6),
            )
            is not None
        )

    def navigate_to_afk_stages_screen(self) -> None:
        logging.info("Navigating to AFK stages screen.")
        self.navigate_to_battle_modes_screen()

        self._tap_till_template_disappears(
            "battle_modes/afk_stage.png", ConfidenceValue("75%")
        )

        self.wait_for_template(
            template="navigation/resonating_hall_label.png",
            crop_regions=CropRegions(left=0.3, right=0.3, top=0.9),
            timeout=self.NAVIGATION_TIMEOUT,
        )
        self.tap(Point(x=550, y=1080), scale=True)  # click rewards popup
        sleep(1)

    def _navigate_to_battle_modes_screen(self) -> None:
        self.tap(self.BATTLE_MODES_POINT, scale=True)
        result = self.wait_for_any_template(
            templates=[
                "battle_modes/afk_stage.png",
                "battle_modes/duras_trials.png",
                "battle_modes/arcane_labyrinth.png",
                "popup/quick_purchase.png",
            ],
            threshold=ConfidenceValue("75%"),
            timeout=self.NAVIGATION_TIMEOUT,
        )

        if result.template == "popup/quick_purchase.png":
            self.press_back_button()
            sleep(1)

        _ = self.wait_for_any_template(
            templates=[
                "battle_modes/afk_stage.png",
                "battle_modes/duras_trials.png",
                "battle_modes/arcane_labyrinth.png",
            ],
            threshold=ConfidenceValue("75%"),
            timeout=self.NAVIGATION_TIMEOUT,
        )

    def navigate_to_battle_modes_screen(self) -> None:
        attempt = 0
        max_attempts = 3
        while True:
            _ = self.navigate_to_current_overview()
            sleep(attempt)
            try:
                self._navigate_to_battle_modes_screen()
            except GameTimeoutError as e:
                attempt += 1
                if attempt >= max_attempts:
                    raise e
                else:
                    continue
            break
        sleep(1)

    def navigate_to_duras_trials_screen(self) -> None:
        logging.info("Navigating to Dura's Trial select")

        def stop_condition() -> bool:
            match = self.game_find_template_match(
                template="duras_trials/featured_heroes.png",
                crop_regions=CropRegions(left=0.7, bottom=0.8),
            )
            return match is not None

        if stop_condition():
            return

        self.navigate_to_battle_modes_screen()
        result = self._find_in_battle_modes(
            template="battle_modes/duras_trials.png",
            timeout_message="Dura's Trial not found.",
        )
        self._tap_till_template_disappears(result.template)
        sleep(1)

        # popups
        self.tap(self.CENTER_POINT, scale=True)
        self.tap(self.CENTER_POINT, scale=True)
        self.tap(self.CENTER_POINT, scale=True)

        self.wait_for_template(
            template="duras_trials/featured_heroes.png",
            crop_regions=CropRegions(left=0.7, bottom=0.8),
            timeout=self.NAVIGATION_TIMEOUT,
        )
        sleep(1)
        return

    def _find_in_battle_modes(
        self, template: str, timeout_message: str
    ) -> TemplateMatchResult:
        if not self.game_find_template_match(template):
            self.swipe_up(sy=1350, ey=500)
            sleep(3)

        return self.wait_for_template(
            template=template,
            timeout_message=timeout_message,
            timeout=self.NAVIGATION_TIMEOUT,
        )

    def navigate_to_legend_trials_select_tower(self) -> None:
        """Navigate to Legend Trials select tower screen."""
        logging.info("Navigating to Legend Trials tower selection")
        self.navigate_to_battle_modes_screen()

        result = self._find_in_battle_modes(
            template="battle_modes/legend_trial.png",
            timeout_message="Could not find Legend Trial Label",
        )

        self._tap_till_template_disappears(result.template)
        self.wait_for_template(
            template="legend_trials/s_header.png",
            crop_regions=CropRegions(right=0.8, bottom=0.8),
            timeout_message="Could not find Season Legend Trial Header",
            timeout=self.NAVIGATION_TIMEOUT,
        )
        sleep(1)

    def navigate_to_arcane_labyrinth(self) -> None:
        # Possibility of getting stuck
        # Back button does not work on Arcane Labyrinth screen
        logging.info("Navigating to Arcane Labyrinth screen")

        def stop_condition() -> bool:
            """Stop condition."""
            match = self.find_any_template(
                templates=[
                    "arcane_labyrinth/select_a_crest.png",
                    "arcane_labyrinth/confirm.png",
                    "arcane_labyrinth/quit.png",
                ],
                crop_regions=CropRegions(top=0.8),
            )

            if match is not None:
                logging.info("Select a Crest screen open")
                return True
            return False

        if stop_condition():
            return

        self.navigate_to_battle_modes_screen()
        result = self._find_in_battle_modes(
            template="battle_modes/arcane_labyrinth.png",
            timeout_message="Could not find Arcane Labyrinth Label",
        )

        self._tap_till_template_disappears(result.template)
        sleep(3)
        _ = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/select_a_crest.png",
                "arcane_labyrinth/confirm.png",
                "arcane_labyrinth/quit.png",
                "arcane_labyrinth/enter.png",
                "arcane_labyrinth/heroes_icon.png",
            ],
            threshold=ConfidenceValue("70%"),
            delay=1,
        )
        return

    def navigate_to_world_chat(self) -> None:
        if self.game_find_template_match("chat/label_world_chat.png"):
            return

        logging.info("Opening World Chat")
        self.navigate_to_current_overview()
        self.device.press_enter()
        sleep(2)

    def navigate_to_team_up_chat(self) -> None:
        if self.game_find_template_match("chat/label_team-up_chat.png"):
            return

        self.navigate_to_world_chat()
        world_chat_label = self.wait_for_template(
            "chat/label_world_chat.png",
            crop_regions=CropRegions(bottom="50%", right="50%", left="10%"),
            timeout=5,
        )
        self.tap(
            world_chat_label.box.top_left + Offset(-70, 550),
            log_message="Opening Team-Up chat",
        )
