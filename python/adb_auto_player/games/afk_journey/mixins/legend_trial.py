"""AFK Journey Season Legend Trial."""

import logging

from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.exceptions import (
    AutoPlayerError,
    AutoPlayerWarningError,
    GameTimeoutError,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.util import SummaryGenerator

from ..base import AFKJourneyBase
from ..battle_state import Mode
from ..gui_category import AFKJCategory


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
        self.battle_state.mode = Mode.LEGEND_TRIALS

        if not self._is_on_season_legend_trial_select():
            try:
                self.navigate_to_legend_trials_select_tower()
            except GameTimeoutError as e:
                logging.error(f"{e} {self.LANG_ERROR}")
                return None

        towers = self.get_config().legend_trials.towers

        factions: list[str] = [
            "Lightbearer",
            "Wilder",
            "Graveborn",
            "Mauler",
        ]

        for faction in factions:
            self.battle_state.faction = faction
            if not self._is_on_season_legend_trial_select():
                self.navigate_to_legend_trials_select_tower()

            if self.battle_state.faction not in towers:
                logging.info(f"{faction}s excluded in Settings")
                continue

            if self.game_find_template_match(
                template=(
                    f"legend_trials/faction_icon_{self.battle_state.faction_lower}.png"
                ),
                crop_regions=CropRegions(right=0.7, top=0.3, bottom=0.1),
            ):
                logging.warning(f"{faction} Tower not available today")
                continue

            result = self.game_find_template_match(
                template=f"legend_trials/banner_{self.battle_state.faction_lower}.png",
                crop_regions=CropRegions(left=0.2, right=0.3, top=0.2, bottom=0.1),
            )
            if result is None:
                logging.error(f"{faction}s Tower not found")
                continue

            logging.info(f"Starting {faction} Tower")
            self.tap(result)
            try:
                self._select_legend_trials_floor()
                self._handle_legend_trials_battle()
            except AutoPlayerWarningError as e:
                logging.warning(f"{e}")
                continue
            except AutoPlayerError as e:
                logging.error(f"{e}")
                continue
        logging.info("Legend Trial finished")
        return None

    def _handle_legend_trials_battle(self) -> None:
        if not self.battle_state.faction:
            raise ValueError("Battle State Faction is required")

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
                if self.battle_state.section_header:
                    logging.info(f"{self.battle_state.section_header} cleared: {count}")
                    SummaryGenerator.increment(
                        self.battle_state.section_header, "Cleared"
                    )

                match match.template:
                    case "next.png":
                        self.tap(match)
                        continue
                    case _:
                        logging.info(f"{self.battle_state.faction} Top Floor Reached")
                return None
            logging.info(f"{self.battle_state.faction} Trials failed")
            return None
        return None

    def _select_legend_trials_floor(self) -> None:
        if not self.battle_state.faction:
            raise ValueError("Battle State Faction is required")

        _ = self.wait_for_template(
            template=f"legend_trials/tower_icon_{self.battle_state.faction_lower}.png",
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
