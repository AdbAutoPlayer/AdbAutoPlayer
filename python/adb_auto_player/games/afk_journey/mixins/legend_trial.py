"""AFK Journey Legend Trial Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player import Coordinates, CropRegions, GameTimeoutError, NotFoundError
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.decorators.register_custom_routine_choice import (
    register_custom_routine_choice,
)
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory


class LegendTrialMixin(AFKJourneyBase, ABC):
    """Legend Trial Mixin."""

    @register_command(
        name="LegendTrial",
        gui=GuiMetadata(
            label="Legend Trial",
            category=AFKJCategory.GAME_MODES,
        ),
    )
    @register_custom_routine_choice(label="Legend Trial")
    def push_legend_trials(self) -> None:
        """Push Legend Trials."""
        self.start_up()
        self.store[self.STORE_MODE] = self.MODE_LEGEND_TRIALS
        try:
            self._navigate_to_legend_trials_select_tower()
        except GameTimeoutError as e:
            logging.error(f"{e} {self.LANG_ERROR}")
            return None

        towers = self.get_config().legend_trials.towers

        results = {}
        factions: list[str] = [
            "lightbearer",
            "wilder",
            "graveborn",
            "mauler",
        ]
        # Season Legend Trial header is visible but there are still animations
        # so we sleep
        sleep(1)
        self.get_screenshot()
        for faction in factions:
            if faction.capitalize() not in towers:
                logging.info(f"{faction.capitalize()}s excluded in config")
                continue

            if self.game_find_template_match(
                template=f"legend_trials/faction_icon_{faction}.png",
                crop=CropRegions(right=0.7, top=0.3, bottom=0.1),
                use_previous_screenshot=True,
            ):
                logging.warning(f"{faction.capitalize()} Tower not available today")
                continue

            result = self.game_find_template_match(
                template=f"legend_trials/banner_{faction}.png",
                crop=CropRegions(left=0.2, right=0.3, top=0.2, bottom=0.1),
                use_previous_screenshot=True,
            )
            if result is None:
                logging.error(f"{faction.capitalize()}s Tower not found")
            else:
                results[faction] = result

        for faction, result in results.items():
            logging.info(f"Starting {faction.capitalize()} Tower")
            if self.game_find_template_match(
                template=f"legend_trials/faction_icon_{faction}.png",
                crop=CropRegions(right=0.7, top=0.3, bottom=0.1),
            ):
                logging.warning(f"{faction.capitalize()} Tower no longer available")
                continue
            self._navigate_to_legend_trials_select_tower()
            self.click(Coordinates(*result))
            try:
                self._select_legend_trials_floor(faction)
            except (GameTimeoutError, NotFoundError) as e:
                logging.error(f"{e}")
                self.press_back_button()
                sleep(3)
                continue
            self._handle_legend_trials_battle(faction)
        logging.info("Legend Trial finished")
        return None

    def _handle_legend_trials_battle(self, faction: str) -> None:
        """Handle Legend Trials battle screen.

        Args:
            faction (str): Faction name.
        """
        count: int = 0
        while True:
            try:
                result: bool = self._handle_battle_screen(
                    self.get_config().legend_trials.use_suggested_formations
                )
            except GameTimeoutError as e:
                logging.warning(f"{e}")
                return None

            if result is True:
                template, x, y = self.wait_for_any_template(
                    templates=[
                        "next.png",
                        "legend_trials/top_floor_reached.png",
                    ]
                )
                count += 1
                logging.info(f"{faction.capitalize()} Trials pushed: {count}")
                match template:
                    case "next.png":
                        self.click(Coordinates(x, y))
                        continue
                    case _:
                        logging.info(f"{faction.capitalize()} Top Floor Reached")
                return None
            logging.info(f"{faction.capitalize()} Trials failed")
            return None
        return None

    def _select_legend_trials_floor(self, faction: str) -> None:
        """Select Legend Trials floor.

        Args:
            faction (str): Faction name.
        """
        logging.debug("_select_legend_trials_floor")
        _ = self.wait_for_template(
            template=f"legend_trials/tower_icon_{faction}.png",
            crop=CropRegions(right=0.8, bottom=0.8),
        )
        challenge_btn = self.wait_for_any_template(
            templates=[
                "legend_trials/challenge_ch.png",
                "legend_trials/challenge_ge.png",
            ],
            threshold=0.8,
            grayscale=True,
            crop=CropRegions(left=0.3, right=0.3, top=0.2, bottom=0.2),
            timeout=self.MIN_TIMEOUT,
            timeout_message="Cannot find Challenge button "
            "assuming Trial is already cleared",
        )
        _, x, y = challenge_btn
        self.click(Coordinates(x, y))

    def _navigate_to_legend_trials_select_tower(self) -> None:
        """Navigate to Legend Trials select tower screen."""

        def check_for_legend_trials_s_header() -> bool:
            header = self.game_find_template_match(
                template="legend_trials/s_header.png",
                crop=CropRegions(right=0.8, bottom=0.8),
            )
            return header is not None

        self._navigate_to_default_state(check_callable=check_for_legend_trials_s_header)

        logging.info("Navigating to Legend Trials tower selection")
        s_header = self.game_find_template_match(
            template="legend_trials/s_header.png",
            crop=CropRegions(right=0.8, bottom=0.8),
            use_previous_screenshot=True,
        )
        if not s_header:
            logging.info("Clicking Battle Modes button")
            self.click(Coordinates(460, 1830), scale=True)
            label = self.wait_for_template(
                template="legend_trials/label.png",
                timeout_message="Could not find Legend Trial Label",
            )
            self.click(Coordinates(*label))
            self.wait_for_template(
                template="legend_trials/s_header.png",
                crop=CropRegions(right=0.8, bottom=0.8),
                timeout_message="Could not find Season Legend Trial Header",
            )
