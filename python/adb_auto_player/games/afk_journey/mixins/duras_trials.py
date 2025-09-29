"""AFK Journey Dura's Trials Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.exceptions import (
    AutoPlayerError,
    AutoPlayerWarningError,
)
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import TemplateMatchResult
from adb_auto_player.util import SummaryGenerator

from ..base import AFKJourneyBase
from ..battle_state import Mode
from ..gui_category import AFKJCategory


class DurasTrialsMixin(AFKJourneyBase, ABC):
    """Dura's Trials Mixin."""

    @register_command(
        name="DurasTrials",
        gui=GUIMetadata(
            label="Dura's Trials",
            category=AFKJCategory.GAME_MODES,
        ),
    )
    @register_custom_routine_choice(label="Dura's Trials")
    def push_duras_trials(self) -> None:
        """Push Dura's Trials."""
        self.start_up()
        self.battle_state.mode = Mode.DURAS_TRIALS
        self.navigate_to_duras_trials_screen()

        try:
            self._handle_dura_screen()
        except AutoPlayerWarningError as e:
            logging.warning(f"{e}")
        except AutoPlayerError as e:
            logging.error(f"{e}")

    def _dura_resolve_state(self) -> TemplateMatchResult:
        while True:
            result = self.wait_for_any_template(
                templates=[
                    "battle/records.png",
                    "duras_trials/battle.png",
                    "duras_trials/sweep.png",
                    "guide/close.png",
                    "guide/next.png",
                    "duras_trials/continue_gray.png",
                ],
            )

            match result.template:
                case "guide/close.png" | "guide/next.png":
                    self._handle_guide_popup()
                case _:
                    break
        return result

    def _handle_dura_screen(self) -> None:
        count = 0

        def handle_duras_pre_battle() -> bool:
            """Handle pre battle steps in normal mode.

            Returns:
                True to continue; False to abort.
            """
            dura_state_result = self._dura_resolve_state()
            match dura_state_result.template:
                case "duras_trials/sweep.png":
                    logging.info("Dura's Trials already cleared")
                    return False
                case "duras_trials/battle.png":
                    self.tap(dura_state_result)
                case "battle/records.png":
                    # No action needed.
                    pass
            return True

        def handle_duras_post_battle() -> bool:
            """Handle post battle actions for normal mode.

            Returns:
                True if the trial is complete, or False to continue pushing battles.
            """
            _ = self.wait_for_any_template(
                templates=[
                    "duras_trials/first_clear_bottom_half.png",
                    "duras_trials/sweep.png",
                ],
                crop_regions=CropRegions(left=0.3, right=0.3, top=0.6, bottom=0.3),
            )
            next_button = self.game_find_template_match(
                template="next.png", crop_regions=CropRegions(left=0.6, top=0.9)
            )
            if next_button is not None:
                nonlocal count
                count += 1
                logging.info(f"Dura's Trials cleared: {count}")
                SummaryGenerator.increment("Dura's Trials", "Cleared")

                self.tap(next_button)
                self.tap(next_button)
                sleep(3)
                return False  # Continue battle loop
            else:
                logging.info("Dura's Trials completed")
                return True  # End loop

        while True:
            if not handle_duras_pre_battle():
                return

            if self._handle_battle_screen(
                self.get_config().duras_trials.use_suggested_formations,
            ):
                if handle_duras_post_battle():
                    return
                continue

            logging.info("Dura's Trials failed")
            return
