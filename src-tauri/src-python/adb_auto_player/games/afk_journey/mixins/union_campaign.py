"""AFK Journey Union Campaign Mixin."""

import logging
from time import sleep

from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.exceptions import (
    AutoPlayerError,
    AutoPlayerWarningError,
    GameTimeoutError,
)
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import TemplateMatchResult
from adb_auto_player.util import SummaryGenerator

from ..base import AFKJourneyBase
from ..battle_state import Mode
from ..gui_category import AFKJCategory


class UnionCampaignMixin(AFKJourneyBase):
    """Union Campaign Mixin.

    Union Campaign is a Guild Mode floor-climb reached from Battle Modes >
    Guild Mode. It has a "Battle" button to fight the current floor and a
    separate "Sweep" button to auto-clear already-cleared floors for
    rewards - Sweep is a limited daily resource the user manages manually,
    so it is never referenced or tapped anywhere in this mixin.
    """

    # Same "Continue" button as the Arena result screen.
    _VICTORY_CONTINUE_TEMPLATE = "arena/continue.png"
    # Bottom button bar: "Records" (formation screen) and "Continue" (VICTORY).
    _POST_BATTLE_CROP_REGIONS = CropRegions(top=0.85)
    _POST_BATTLE_MAX_CONTINUE_TAPS = 3

    @register_command(
        name="UnionCampaign",
        gui=GUIMetadata(
            label="Union Campaign",
            category=AFKJCategory.GAME_MODES,
            tooltip="Push Union Campaign floors in Guild Mode",
        ),
    )
    @register_custom_routine_choice(label="Union Campaign")
    def push_union_campaign(self) -> None:
        """Push Union Campaign floors."""
        self.start_up()
        self.battle_state.mode = Mode.UNION_CAMPAIGN
        self.navigate_to_union_campaign_screen()

        try:
            self._handle_union_campaign_screen()
        except AutoPlayerWarningError as e:
            logging.warning(f"{e}")
        except AutoPlayerError as e:
            logging.error(f"{e}")

    def _union_campaign_resolve_state(self) -> TemplateMatchResult:
        while True:
            result = self.wait_for_any_template(
                templates=[
                    "union_campaign/battle.png",
                    "battle/records.png",
                    "guide/close.png",
                    "guide/next.png",
                    "battle/skip.png",
                    "battle/skip_orange.png",
                    "quests/skip.png",
                ],
            )

            match result.template:
                case (
                    "guide/close.png"
                    | "guide/next.png"
                    | "battle/skip.png"
                    | "battle/skip_orange.png"
                    | "quests/skip.png"
                ):
                    if "skip" in result.template:
                        logging.info(f"Skip button found ({result.template}), tapping")
                    self.tap(result)
                    sleep(1)
                    self._handle_guide_popup()
                case _:
                    break
        return result

    def _handle_union_campaign_screen(self) -> None:
        count = 0

        def handle_pre_battle() -> None:
            state_result = self._union_campaign_resolve_state()
            if state_result.template == "union_campaign/battle.png":
                self._tap_till_template_disappears("union_campaign/battle.png")
                self.sleep_navigation()

        def handle_post_battle() -> bool:
            """Handle post battle actions.

            A win shows the VICTORY screen; its "Continue" button (already
            tapped by the battle result handling) loads straight into the next
            floor's formation screen, recognizable by its "Records" button.

            Returns:
                True if Union Campaign is complete, False to keep pushing.
            """
            nonlocal count
            count += 1
            logging.info(f"Union Campaign cleared: {count}")
            SummaryGenerator.increment("Union Campaign", "Cleared")

            for _ in range(self._POST_BATTLE_MAX_CONTINUE_TAPS):
                try:
                    result = self.wait_for_any_template(
                        templates=[
                            "battle/records.png",
                            self._VICTORY_CONTINUE_TEMPLATE,
                        ],
                        crop_regions=self._POST_BATTLE_CROP_REGIONS,
                        timeout=self.template_timeout,
                        # The order re-check only waits 3s: if Continue is
                        # seen right before the loading screen, it finds
                        # nothing and times out while the next floor loads.
                        # The two templates never share a screen anyway.
                        ensure_order=False,
                    )
                except GameTimeoutError:
                    break
                if result.template == "battle/records.png":
                    return False  # Next floor ready, continue battle loop
                # VICTORY screen still up. It lingers for a moment after the
                # Continue tap before the loading screen starts, so wait for it
                # to go away instead of re-checking (and re-tapping) right away.
                self.tap(result)
                try:
                    self.wait_until_template_disappears(
                        self._VICTORY_CONTINUE_TEMPLATE,
                        crop_regions=self._POST_BATTLE_CROP_REGIONS,
                        timeout=self.fast_timeout,
                    )
                except GameTimeoutError:
                    continue  # Tap was missed, try again

            # TODO: the screen shown after the last floor is unknown.
            self.capture_debug_screenshot("union_campaign_no_next_floor")
            logging.info("Union Campaign completed")
            return True  # End loop

        while True:
            handle_pre_battle()

            if self._handle_battle_screen(
                self.settings.union_campaign.use_suggested_formations,
            ):
                if handle_post_battle():
                    return
                continue

            logging.info("Union Campaign: floor not cleared, no more formations to try")
            return
