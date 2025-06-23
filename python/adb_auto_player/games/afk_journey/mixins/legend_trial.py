"""AFK Journey Season Legend Trial."""

import logging

from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.exceptions import (
    AutoPlayerError,
    AutoPlayerWarningError,
    GameTimeoutError,
)
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.util import SummaryGenerator


# Tested S4 2025.05.23
class SeasonLegendTrial(AFKJourneyBase):
    """Season Legend Trial Mixin."""

    @register_command(
        name="LegendTrial",
        gui=GUIMetadata(
            label="Season Legend Trial",
            category=AFKJCategory.GAME_MODES,
        ),
    )
    @register_custom_routine_choice(label="Season Legend Trial")
    def push_legend_trials(self) -> None:
        """Push Legend Trials."""
        self.start_up()
        self.store[self.STORE_MODE] = self.MODE_LEGEND_TRIALS

        if not self._is_on_season_legend_trial_select():
            try:
                self.navigate_to_legend_trials_select_tower()
            except GameTimeoutError as e:
                logging.error(f"{e} {self.LANG_ERROR}")
                return None

        towers = self.get_config().legend_trials.towers

        factions: list[str] = [
            "lightbearer",
            "wilder",
            "graveborn",
            "mauler",
        ]

        for faction in factions:
            if not self._is_on_season_legend_trial_select():
                self.navigate_to_legend_trials_select_tower()

            if faction.capitalize() not in towers:
                logging.info(f"{faction.capitalize()}s excluded in config")
                continue

            if self.game_find_template_match(
                template=f"legend_trials/faction_icon_{faction}.png",
                crop_regions=CropRegions(right=0.7, top=0.3, bottom=0.1),
            ):
                logging.warning(f"{faction.capitalize()} Tower not available today")
                continue

            result = self.game_find_template_match(
                template=f"legend_trials/banner_{faction}.png",
                crop_regions=CropRegions(left=0.2, right=0.3, top=0.2, bottom=0.1),
            )
            if result is None:
                logging.error(f"{faction.capitalize()}s Tower not found")
                continue

            logging.info(f"Starting {faction.capitalize()} Tower")
            self.tap(result)
            try:
                self._select_legend_trials_floor(faction)
                self._handle_legend_trials_battle(faction)
            except AutoPlayerWarningError as e:
                logging.warning(f"{e}")
                continue
            except AutoPlayerError as e:
                logging.error(f"{e}")
                continue
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
                    self.get_config().legend_trials.use_suggested_formations,
                    self.get_config().legend_trials.skip_manual_formations,
                )
            except GameTimeoutError as e:
                logging.error(f"{e}")
                return None

            if result is True:
                match = self.wait_for_any_template(
                    templates=[
                        "next.png",
                        "legend_trials/top_floor_reached.png",
                    ]
                )
                count += 1
                logging.info(f"{faction.capitalize()} Trials pushed: {count}")
                SummaryGenerator.add_count(f"{faction.capitalize()} Trials")

                match match.template:
                    case "next.png":
                        self.tap(match)
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
            crop_regions=CropRegions(right=0.8, bottom=0.8),
        )
        challenge_btn = self.wait_for_any_template(
            templates=[
                "legend_trials/challenge_ch.png",
                "legend_trials/challenge_ge.png",
            ],
            threshold=ConfidenceValue("80%"),
            grayscale=True,
            crop_regions=CropRegions(left=0.3, right=0.3, top=0.2, bottom=0.2),
            timeout=self.MIN_TIMEOUT,
            timeout_message="Cannot find Challenge button "
            "assuming Trial is already cleared",
        )
        self.tap(challenge_btn)

    def _is_on_season_legend_trial_select(self) -> bool:
        return (
            self.game_find_template_match(
                template="legend_trials/s_header.png",
                crop_regions=CropRegions(right=0.8, bottom=0.8),
            )
            is not None
        )
