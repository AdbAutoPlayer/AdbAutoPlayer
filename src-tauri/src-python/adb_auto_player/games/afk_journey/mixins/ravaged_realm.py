"""AFK Journey Ravaged Realm Mixin."""

import logging
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameActionFailedError, GameTimeoutError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions


class RavagedRealmMixin(AFKJourneyBase):
    """Ravaged Realm Mixin."""

    @register_command(
        name="RavagedRealm",
        gui=GUIMetadata(
            label="Ravaged Realm",
            category=AFKJCategory.EVENTS_AND_OTHER,
            tooltip="Complete the Ravaged Realm event automatically",
        ),
    )
    def run_ravaged_realm(self) -> None:
        """Complete Ravaged Realm."""
        self.start_up()

        try:
            self._enter_ravaged_realm()
            self.sleep_navigation()

            if self._try_skip():
                logging.info("Ravaged Realm skipped successfully.")
                return

            self._run_battle()
        except (GameTimeoutError, GameActionFailedError) as e:
            logging.error(str(e))
            return

        logging.info("Ravaged Realm finished.")

    ############################## Helper Functions ##############################

    def _enter_ravaged_realm(self) -> None:
        """Navigate to the Ravaged Realm screen via hamburger menu > Events."""
        logging.info("Entering Ravaged Realm...")
        self.navigate_to_world()
        logging.info("Opening hamburger menu...")
        self._tap_till_template_disappears(template="navigation/hamburger_menu")
        sleep(2)
        logging.info("Tapping Events...")
        self._tap_till_template_disappears(template="dailies/hamburger/events")
        sleep(2)
        logging.info("Looking for Ravaged Realm label...")
        label = self.wait_for_template(
            "event/ravaged_realm/label.png",
            threshold=ConfidenceValue("75%"),
            timeout_message="Failed to find Ravaged Realm in the events list.",
            timeout=self.min_timeout,
        )
        self.tap(label)
        self.sleep_navigation()

    def _try_skip(self) -> bool:
        """Check for and handle the Skip button.

        If the Skip button is present the run has already been completed today:
        tap Skip → confirm the popup → tap to close the rewards screen.

        Returns:
            True if the skip flow was executed, False if Battle should be run instead.
        """
        skip = self.find_any_template(
            templates=["battle/skip.png", "battle/skip_orange.png"],
        )
        if skip is None:
            return False

        logging.info("Skip available - claiming skip rewards.")
        self.tap(skip)
        self.sleep_action()

        self._tap_till_template_disappears(template="navigation/confirm")
        self.sleep_action()

        # Close the rewards list by tapping anywhere on it.
        self.tap(self.CENTER_POINT)
        self.sleep_navigation()
        return True

    def _run_battle(self) -> None:
        """Tap Battle to enter prep screen, copy first Records formation, and start."""
        logging.info("Starting Ravaged Realm battle...")
        self.sleep_navigation()

        # Tap the Battle button to enter the battle prep screen.
        battle_btn = self.wait_for_template(
            "battle/battle.png",
            timeout_message="Failed to find Battle button.",
            timeout=self.min_timeout,
        )
        self.tap(battle_btn)
        self.sleep_navigation()

        # Open Records (community formations).
        # Template already exists: battle/records.png
        records = self.wait_for_template(
            "battle/records.png",
            timeout_message="Failed to find Records button.",
            timeout=self.min_timeout,
        )
        self.tap(records)
        self.sleep_navigation()

        # Select the first formation via the Use button.
        # Template already exists: battle/use.png
        use_btn = self.wait_for_template(
            "battle/use.png",
            timeout_message="Failed to find Use button in Records.",
            timeout=self.min_timeout,
        )
        self.tap(use_btn)
        self.sleep_navigation()

        # Press Skip twice to copy the formation to both slots.
        for i in range(2):
            try:
                skip_btn = self.wait_for_any_template(
                    templates=["event/ravaged_realm/skip.png"],
                    timeout=self.template_timeout,
                    timeout_message=f"Failed to find Skip button (press {i + 1}/2).",
                )
                self.tap(skip_btn)
                self.sleep_action()
            except GameTimeoutError as fail:
                logging.error(f"{fail}")
                return

        self.sleep_navigation()
        logging.info("Initiating battle...")
        self.tap(Point(850, 1780))
        self.sleep_navigation()

        logging.info("Waiting for battle to complete...")
        try:
            match = self.wait_for_any_template(
                templates=self._get_battle_over_templates(),
                timeout=self.BATTLE_TIMEOUT,
                crop_regions=CropRegions(top=0.4),
                delay=1.0,
                timeout_message="Battle over screen not found after timeout.",
            )
            logging.info("Battle complete. Dismissing result screen...")
            self.sleep_navigation()
            self.tap(match)
            self.sleep_navigation()
            self.tap(Point(550, 1800))
            self.sleep_navigation()
            self.tap(self.CENTER_POINT)
            self.sleep_navigation()
        except GameTimeoutError as fail:
            logging.error(str(fail))
