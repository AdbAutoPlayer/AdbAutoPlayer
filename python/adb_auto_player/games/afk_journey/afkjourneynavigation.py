import logging
from abc import ABC
from time import sleep

from adb_auto_player import Coordinates, CropRegions, Game
from adb_auto_player.exceptions import (
    GameActionFailedError,
    GameNotRunningOrFrozenError,
)


class AFKJourneyNavigation(Game, ABC):
    # Timeouts
    NAVIGATION_TIMEOUT = 10.0

    # Coords
    CENTER_COORDS = Coordinates(x=1080 // 2, y=1920 // 2)
    RESONATING_HALL_COORDS = Coordinates(x=620, y=1830)
    BATTLE_MODES_COORDS = Coordinates(x=460, y=1830)

    def navigate_to_default_state(
        self,
    ) -> None:
        """Navigate to main default screen."""
        templates = [
            "navigation/notice.png",
            "navigation/confirm.png",
            "navigation/time_of_day.png",
            "navigation/dotdotdot.png",
            "battle/copy.png",
            "guide/close.png",
            "guide/next.png",
            "battle/copy.png",
            "login/claim.png",
            "arcane_labyrinth/back_arrow.png",
        ]

        max_attempts = 40
        restart_attempts = 20
        attempts = 0

        while True:
            if not self.is_game_running():
                logging.error("Game not running.")
                self._handle_restart(templates)
            if attempts >= restart_attempts:
                logging.warning("Failed to navigate to default state.")
                self._handle_restart(templates)
            if attempts >= max_attempts:
                raise GameNotRunningOrFrozenError(
                    "Failed to navigate to default state."
                )
            attempts += 1

            result = self.find_any_template(templates)

            if result is None:
                logging.debug("back")
                self.press_back_button()
                sleep(3)
                continue

            template, x, y = result
            match template:
                case "navigation/time_of_day.png":
                    break
                case "navigation/notice.png":
                    # TODO whats this?, make constant
                    self.tap(Coordinates(x=530, y=1630), scale=True)
                    sleep(3)
                case "navigation/confirm.png":
                    self._handle_confirm_button(Coordinates(x=x, y=y))
                case "navigation/dotdotdot.png":
                    self.press_back_button()
                    sleep(1)
                case _:
                    self.tap(Coordinates(x=x, y=y))
                    sleep(1)
        sleep(1)

    def _handle_restart(self, templates: list[str]) -> None:
        logging.warning("Trying to restart AFK Journey.")
        self.force_stop_game()
        self.start_game()
        max_attempts = 40
        attempts = 0
        while not self.find_any_template(templates) and self.is_game_running():
            if attempts >= max_attempts:
                raise GameNotRunningOrFrozenError(
                    "Failed to navigate to default state."
                )
            attempts += 1
            self.tap(self.CENTER_COORDS)
            sleep(3)
        sleep(1)

    def _handle_confirm_button(self, coords: Coordinates) -> None:
        if self.game_find_template_match(
            "navigation/exit_the_game.png",
        ):
            x_btn: tuple[int, int] | None = self.game_find_template_match(
                "navigation/x.png",
            )
            if x_btn:
                logging.debug("x")
                self.tap(Coordinates(*x_btn))
                sleep(1)
            self.press_back_button()
        else:
            self.tap(coords)
        sleep(1)

    def navigate_to_resonating_hall(self) -> None:
        logging.info("Navigating to the Resonating Hall.")
        self.navigate_to_default_state()

        max_click_count = 3
        click_count = 0
        while self._can_see_time_of_day_button():
            self.tap(self.RESONATING_HALL_COORDS, scale=True)
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
            timeout=AFKJourneyNavigation.NAVIGATION_TIMEOUT,
        )

    def _can_see_time_of_day_button(self):
        return (
            self.game_find_template_match(
                "navigation/time_of_day.png",
                crop=CropRegions(left=0.6, right=0.1, bottom=0.8),
            )
            is not None
        )

    def navigate_to_afk_stages_screen(self) -> None:
        logging.info("Navigating to AFK stages screen.")
        self.navigate_to_battle_modes_screen()

        self._tap_till_template_disappears(
            "battle_modes/afk_stage.png", threshold=0.75, delay=2
        )

        self.wait_for_template(
            template="navigation/resonating_hall_label.png",
            crop=CropRegions(left=0.3, right=0.3, top=0.9),
            timeout=AFKJourneyNavigation.NAVIGATION_TIMEOUT,
        )

    def navigate_to_battle_modes_screen(self) -> None:
        self.navigate_to_default_state()

        self.tap(self.BATTLE_MODES_COORDS, scale=True)
        _ = self.wait_for_any_template(
            templates=[
                "battle_modes/afk_stage.png",
                "battle_modes/duras_trials.png",
                "battle_modes/arcane_labyrinth.png",
            ],
            threshold=0.75,
            timeout=AFKJourneyNavigation.NAVIGATION_TIMEOUT,
        )
        sleep(1)

    def navigate_to_duras_trials_screen(self) -> None:
        logging.info("Navigating to Dura's Trial select")

        def stop_condition() -> bool:
            match = self.game_find_template_match(
                template="duras_trials/featured_heroes.png",
                crop=CropRegions(left=0.7, bottom=0.8),
            )
            return match is not None

        if stop_condition():
            return

        self.navigate_to_battle_modes_screen()
        coords = self._find_on_battle_modes(
            template="battle_modes/duras_trials.png",
            timeout_message="Dura's Trial not found.",
        )
        self.tap(coords)
        self.wait_for_template(
            template="duras_trials/featured_heroes.png",
            crop=CropRegions(left=0.7, bottom=0.8),
            timeout=AFKJourneyNavigation.NAVIGATION_TIMEOUT,
        )
        return

    def _find_on_battle_modes(self, template: str, timeout_message: str) -> Coordinates:
        if not self.game_find_template_match(template):
            self.swipe_up(sy=1350, ey=500)

        label = self.wait_for_template(
            template=template,
            timeout_message=timeout_message,
            timeout=AFKJourneyNavigation.NAVIGATION_TIMEOUT,
        )
        return Coordinates(*label)

    def navigate_to_legend_trials_select_tower(self) -> None:
        """Navigate to Legend Trials select tower screen."""
        logging.info("Navigating to Legend Trials tower selection")
        self.navigate_to_battle_modes_screen()

        coords = self._find_on_battle_modes(
            template="battle_modes/legend_trial.png",
            timeout_message="Could not find Legend Trial Label",
        )

        self.tap(coords)
        self.wait_for_template(
            template="legend_trials/s_header.png",
            crop=CropRegions(right=0.8, bottom=0.8),
            timeout_message="Could not find Season Legend Trial Header",
            timeout=AFKJourneyNavigation.NAVIGATION_TIMEOUT,
        )
        sleep(1)

    def navigate_to_arcane_labyrinth(self) -> None:
        # Possibility of getting stuck
        # Back button does not work on Arcane Labyrinth screen
        logging.info("Navigating to Arcane Labyrinth screen")

        def stop_condition() -> bool:
            """Stop condition."""
            match: tuple[str, int, int] | None = self.find_any_template(
                templates=[
                    "arcane_labyrinth/select_a_crest.png",
                    "arcane_labyrinth/confirm.png",
                    "arcane_labyrinth/quit.png",
                ],
                crop=CropRegions(top=0.8),
            )

            if match is not None:
                logging.info("Select a Crest screen open")
                return True
            return False

        if stop_condition():
            return

        self.navigate_to_battle_modes_screen()
        coords = self._find_on_battle_modes(
            template="battle_modes/arcane_labyrinth.png",
            timeout_message="Could not find Arcane Labyrinth Label",
        )

        self.tap(coords)
        _ = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/enter.png",
                "arcane_labyrinth/heroes_icon.png",
            ],
            threshold=0.7,
            crop=CropRegions(left=0.3, top=0.8),
            timeout=AFKJourneyNavigation.NAVIGATION_TIMEOUT,
        )
        return
