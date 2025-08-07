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
from adb_auto_player.models.geometry import Coordinates, Point
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

        rate_up_banners = self.find_all_template_matches(
            template="duras_trials/rate_up.png",
            grayscale=True,
            crop_regions=CropRegions(top=0.6, bottom=0.2),
        )

        if not rate_up_banners:
            logging.warning(
                "Dura's Trials Rate Up banners could not be found, Stopping"
            )
            return None

        first_banner = True
        for banner in rate_up_banners:
            self.battle_state.mode = Mode.DURAS_TRIALS
            if not first_banner:
                self.navigate_to_duras_trials_screen()
            try:
                self._handle_dura_screen(banner)
            except AutoPlayerWarningError as e:
                logging.warning(f"{e}")
            except AutoPlayerError as e:
                logging.error(f"{e}")

            self.battle_state.mode = Mode.DURAS_NIGHTMARE_TRIALS
            self.navigate_to_duras_trials_screen()
            try:
                self._handle_dura_screen(banner, nightmare_mode=True)
            except AutoPlayerWarningError as e:
                logging.warning(f"{e}")
            except AutoPlayerError as e:
                logging.error(f"{e}")
            first_banner = False

        return None

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

    def _handle_dura_screen(  # noqa: PLR0915 - TODO: Refactor better
        self, coordinates: Coordinates, nightmare_mode: bool = False
    ) -> None:
        # y+100 clicks closer to center of the button instead of rate up text
        offset = int(self.scale_factor * 100)
        self.tap(Point(coordinates.x, coordinates.y + offset))
        count = 0

        def handle_nightmare_pre_battle() -> bool:
            """Handle pre battle steps in nightmare mode.

            Returns:
                True to continue; False to abort.
            """
            # Get current state; if we already see records, skip nightmare handling.
            match = self._dura_resolve_state()

            if match.template == "duras_trials/continue_gray.png":
                return False
            if match.template == "battle/records.png":
                return True

            nightmare = self.game_find_template_match(
                template="duras_trials/nightmare.png",
                crop_regions=CropRegions(left=0.6, top=0.9),
            )
            if nightmare is None:
                logging.warning("Nightmare Button not found")
                return False
            self.tap(nightmare)

            nightmare_result = self.wait_for_any_template(
                templates=[
                    "duras_trials/nightmare_skip.png",
                    "duras_trials/nightmare_swords.png",
                    "duras_trials/cleared.png",
                ],
                crop_regions=CropRegions(top=0.7, bottom=0.1),
            )
            match nightmare_result.template:
                case "duras_trials/nightmare_skip.png":
                    self.tap(nightmare_result)
                    self.wait_until_template_disappears(
                        "duras_trials/nightmare_skip.png",
                        crop_regions=CropRegions(top=0.7, bottom=0.1),
                    )
                    self.tap(nightmare_result)
                    self.wait_for_template(
                        "duras_trials/nightmare_swords.png",
                        crop_regions=CropRegions(top=0.7, bottom=0.1),
                    )
                    self.tap(nightmare_result)
                case "duras_trials/nightmare_swords.png":
                    self.tap(nightmare_result)
                case "duras_trials/cleared.png":
                    logging.info("Nightmare Trial already cleared")
                    return False
            return True

        def handle_non_nightmare_pre_battle() -> bool:
            """Handle pre battle steps in normal mode.

            Returns:
                True to continue; False to abort.
            """
            dura_state_result = self._dura_resolve_state()
            match dura_state_result.template:
                case "duras_trials/sweep.png":
                    logging.info("Dura's Trial already cleared")
                    return False
                case "duras_trials/battle.png":
                    self.tap(dura_state_result)
                case "battle/records.png":
                    # No action needed.
                    pass
            return True

        def handle_non_nightmare_post_battle() -> bool:
            """Handle post battle actions for normal mode.

            Returns:
                True if the trial is complete, or False to continue pushing battles.
            """
            _ = self.wait_for_any_template(
                templates=["duras_trials/first_clear.png", "duras_trials/sweep.png"],
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
                logging.info("Dura's Trial completed")
                return True  # End loop

        def handle_nightmare_post_battle() -> bool:
            """Handle post battle actions for nightmare mode.

            Returns:
            True if the trial is complete, or False to continue.
            """
            nonlocal count
            count += 1
            logging.info(f"Dura's Nightmare Trials cleared: {count}")
            SummaryGenerator.increment("Dura's Nightmare Trials", "Cleared")

            if self.game_find_template_match(
                template="duras_trials/continue_gray.png",
                crop_regions=CropRegions(top=0.8),
            ):
                logging.info("Nightmare Trial completed")
                return True
            return False

        while True:
            # Pre battle handling based on mode.
            if nightmare_mode:
                if not handle_nightmare_pre_battle():
                    return
            elif not handle_non_nightmare_pre_battle():
                return

            # Handle the battle screen.
            result = self._handle_battle_screen(
                self.get_config().duras_trials.use_suggested_formations,
            )

            if result is True:
                if nightmare_mode:
                    if handle_nightmare_post_battle():
                        return
                    # Else continue to the next loop iteration.
                elif handle_non_nightmare_post_battle():
                    return
                # Else continue to the next loop iteration.
            else:
                logging.info("Dura's Trial failed")
                return
