"""AFK Journey Ravaged Realm Mixin."""

import logging
from time import sleep

from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.exceptions import GameActionFailedError, GameTimeoutError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.battle_state import Mode
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import TemplateMatchResult


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
    @register_custom_routine_choice(label="Ravaged Realm")
    def run_ravaged_realm(self) -> None:
        """Complete Ravaged Realm."""
        self.battle_state.mode = Mode.RAVAGED_REALM
        self.start_up()

        try:
            self._enter_ravaged_realm()
            self.sleep_navigation()

            if self._try_skip():
                logging.info("Ravaged Realm skipped successfully.")
                return

            self._run_all_squads()
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
        # Allow initial event entrance animation to finish completely
        sleep(8)

    def _try_skip(self) -> bool:
        """Check for and handle the Skip button.

        If the Skip button is present the run has already been completed today:
        tap Skip → confirm the popup → tap to close the rewards screen.

        Returns:
            True if the skip flow was executed, False if Battle should be run instead.
        """
        skip = self.game_find_template_match(
            "event/ravaged_realm/skip.png",
            threshold=ConfidenceValue("80%"),
            crop_regions=CropRegions(top=0.7),
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

    def _copy_ravaged_realm_formation(self, prep_match: TemplateMatchResult) -> bool:
        """Open Records and copy the first community formation."""
        try:
            if prep_match.template == "battle/records.png":
                records = prep_match
            else:
                records = self.wait_for_template(
                    "battle/records.png",
                    timeout_message="Failed to find Records button.",
                    timeout=self.min_timeout,
                )
            self.tap(records)
            self.sleep_navigation()

            # Select the first formation via the Use button.
            use_btn = self.wait_for_template(
                "battle/use.png",
                timeout_message="Failed to find Use button in Records.",
                timeout=self.min_timeout,
            )
            self.tap(use_btn)
            self.sleep_navigation()

            # Press Skip twice to copy the formation to both slots.
            for i in range(2):
                skip_btn = self.wait_for_any_template(
                    templates=["event/ravaged_realm/skip.png"],
                    timeout=self.template_timeout,
                    timeout_message=f"Failed to find Skip (press {i + 1}/2).",
                )
                self.tap(skip_btn)
                self.sleep_action()
            return True
        except GameTimeoutError as fail:
            logging.error(f"{fail}")
            return False

    # ruff: noqa: PLR0915
    def _run_battle(self) -> None:
        """Tap Battle to enter prep screen, copy first Records formation, and start."""
        attempts = self.settings.ravaged_realm.attempts
        spend_gold = self.settings.ravaged_realm.spend_gold

        for attempt in range(1, attempts + 1):
            logging.info(
                f"Starting Ravaged Realm battle (Attempt {attempt}/{attempts})..."
            )
            self.sleep_navigation()
            # Tap the Battle button to enter the battle prep screen.
            try:
                battle_btn = self.wait_for_template(
                    "battle/battle.png",
                    threshold=ConfidenceValue("15%"),
                    crop_regions=CropRegions(top=0.6, bottom=0.1),
                    timeout_message="Failed to find Battle button even at 15% threshold.",
                    timeout=self.min_timeout,
                )
                self.tap(battle_btn)

                # Wait for prep screen interface OR gold purchase popup
                prep_match = self.wait_for_any_template(
                    templates=[
                        "battle/records.png",
                        "battle/formations_icon.png",
                        "battle/spend.png",
                        "battle/gold.png",
                        "navigation/confirm.png",
                        "confirm_text.png",
                    ],
                    crop_regions=CropRegions(top=0.4),
                    timeout=self.template_timeout,
                    timeout_message="Failed to load battle prep screen.",
                )

                # If we caught a gold purchase popup instead of the prep screen
                if prep_match.template in [
                    "battle/spend.png",
                    "battle/gold.png",
                    "navigation/confirm.png",
                    "confirm_text.png",
                ]:
                    if not spend_gold:
                        logging.warning("No attempts. Not spending gold. Returning.")
                        self.press_back_button()
                        return
                    logging.info("Confirming gold purchase for battle attempt...")
                    self._click_confirm_on_popup()
                    self.sleep_navigation()

                    # Now wait for the actual prep screen to load after purchase
                    prep_match = self.wait_for_any_template(
                        templates=[
                            "battle/records.png",
                            "battle/formations_icon.png",
                        ],
                        crop_regions=CropRegions(top=0.5),
                        timeout=self.template_timeout,
                        timeout_message="Failed to load prep screen after purchase.",
                    )
            except GameTimeoutError as fail:
                logging.error(str(fail))
                return

            if self.settings.ravaged_realm.use_suggested_formations:
                if not self._copy_ravaged_realm_formation(prep_match):
                    return
                self.sleep_navigation()
            else:
                logging.info("Using current formation (skipping Records).")

            logging.info("Initiating battle...")
            try:
                self.tap(Point(850, 1780))
                self._tap_coordinates_till_template_disappears(
                    coordinates=Point(850, 1780),
                    template=prep_match.template,
                    crop_regions=CropRegions(top=0.5),
                    delay=2.0,
                )
            except GameActionFailedError:
                logging.warning("Failed to start Battle. Are heroes selected?")
                return
            self.sleep_action()

            logging.info("Waiting for battle to complete or skip button...")
            try:
                templates = [
                    *self._get_battle_over_templates(),
                    "battle/skip.png",
                    "battle/skip_orange.png",
                ]
                match = self.wait_for_any_template(
                    templates=templates,
                    timeout=self.BATTLE_TIMEOUT,
                    crop_regions=CropRegions(top=0.4),
                    delay=1.0,
                    timeout_message="Battle over screen not found after timeout.",
                )

                if match.template in ["battle/skip.png", "battle/skip_orange.png"]:
                    logging.info("Live battle skip button detected. Tapping skip...")
                    self.tap(match)
                    self.sleep_action()

                    match = self.wait_for_any_template(
                        templates=self._get_battle_over_templates(),
                        timeout=self.template_timeout,
                        crop_regions=CropRegions(top=0.4),
                        delay=1.0,
                        timeout_message="Battle over screen not found after skipping.",
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
                break

    def _detect_faction_states(
        self,
        faction_templates: dict[str, str],
        open_templates: dict[str, str],
        tab_region: CropRegions,
    ) -> list[tuple[int, str, str, Point, float]]:
        """Scan for all possible faction states and return detected points."""
        detected = []
        for faction, locked_tpl in faction_templates.items():
            # Check Locked state
            match_locked = self.game_find_template_match(
                locked_tpl, crop_regions=tab_region, threshold=ConfidenceValue("30%")
            )
            if match_locked:
                detected.append(
                    (
                        match_locked.x,
                        faction,
                        "Locked",
                        Point(match_locked.x, match_locked.y),
                        match_locked.confidence.value,
                    )
                )

            # Check Open state
            open_tpl = open_templates.get(faction)
            if open_tpl:
                match_open = self.game_find_template_match(
                    open_tpl,
                    crop_regions=tab_region,
                    threshold=ConfidenceValue("30%"),
                )
                if match_open:
                    detected.append(
                        (
                            match_open.x,
                            faction,
                            "Open",
                            Point(match_open.x, match_open.y),
                            match_open.confidence.value,
                        )
                    )
        return detected

    def _get_squad_states(self) -> dict[str, Point]:
        """Detect squad tab locations and states using relative ordering.

        Returns:
            A dictionary mapping faction names to their clickable Points,
            only for squads that are not locked.
        """
        faction_templates = {
            "Graveborn": "event/ravaged_realm/Immortal_Squad_Locked.png",
            "Mauler": "event/ravaged_realm/Dauntless_Squad_Locked.png",
            "Wilder": "event/ravaged_realm/Sylvan_Squad_Locked.png",
            "Lightbearer": "event/ravaged_realm/Aurora_Squad_Locked.png",
        }
        open_templates = {
            "Graveborn": "event/ravaged_realm/Immortal_Squad_Open.png",
            "Wilder": "event/ravaged_realm/Sylvan_Squad_Open.png",
            "Lightbearer": "event/ravaged_realm/Aurora_Squad_Open.png",
        }

        active_squads = {}
        tab_region = CropRegions(top=0.7)
        detected_points = self._detect_faction_states(
            faction_templates, open_templates, tab_region
        )

        # Determine average Y coordinate for tabs
        y_coords = [p[3].y for p in detected_points]
        avg_y = int(sum(y_coords) / len(y_coords)) if y_coords else 1830

        # Fallback for Immortal (Graveborn)
        if not any(d[1] == "Graveborn" for d in detected_points):
            match_immortal = self.game_find_template_match(
                faction_templates["Graveborn"],
                crop_regions=CropRegions(left=0, right=0.6, top=0.7),
                threshold=ConfidenceValue("30%"),
            )
            if match_immortal:
                detected_points.append(
                    (
                        match_immortal.x,
                        "Graveborn",
                        "Locked",
                        Point(match_immortal.x, match_immortal.y),
                        match_immortal.confidence.value,
                    )
                )
            else:
                # Absolute fallback if everything fails for Graveborn
                detected_points.append((150, "Graveborn", "Open", Point(150, avg_y), 1.0))

        # Resolve best match: pick the state with higher confidence for each faction
        faction_best = {}
        for _, faction, state, point, confidence in detected_points:
            if faction not in faction_best:
                faction_best[faction] = (state, point, confidence)
            else:
                prev_state, prev_point, prev_conf = faction_best[faction]
                if confidence > prev_conf:
                    faction_best[faction] = (state, point, confidence)

        for faction, (state, point, conf) in faction_best.items():
            # Calculate search window centered on the tab, ensuring it's at least 450px wide
            # template is 299x142, so we need some margin.
            window_width = 450
            left_px = point.x - (window_width // 2)
            right_px = point.x + (window_width // 2)

            # Clamp and shift window if it goes out of bounds
            if left_px < 0:
                right_px -= left_px
                left_px = 0
            if right_px > 1080:
                left_px -= (right_px - 1080)
                right_px = 1080
            
            # Ensure left_px doesn't become negative after shift (edge case for small screens)
            left_px = max(0, left_px)

            # We now rely solely on the best match between Locked and Open templates
            # as the secondary padlock check was too prone to false positives (0.45+ on active squads).
            if state == "Locked":
                logging.info(f"Squad {faction} is locked.")
                continue

            active_squads[faction] = point
            logging.info(f"Squad {faction} is active.")

        return active_squads

    def _run_all_squads(self) -> None:
        """Iterate through all 4 squad tabs and run battle attempts."""
        configured_squads = self.settings.ravaged_realm.squads
        active_squad_points = self._get_squad_states()

        if not active_squad_points:
            logging.warning("No active squads detected in Ravaged Realm.")
            return

        # Faction order to maintain consistency
        faction_order = ["Graveborn", "Mauler", "Wilder", "Lightbearer"]

        for faction in faction_order:
            if faction not in active_squad_points:
                continue

            if faction not in configured_squads:
                logging.info(f"Squad {faction} disabled in settings. Skipping.")
                continue

            tab_point = active_squad_points[faction]
            logging.info(f"Switching to squad: {faction}...")
            self.tap(tab_point)
            self.sleep_navigation()
            self.sleep_navigation()
            sleep(2)

            # Verification of Battle button (restrict region to avoid tabs at bottom)
            # Using a very low threshold (15%) because seasonal UI gradients cause low confidence,
            # but in this restricted region, the best match is almost certainly the button.
            battle_match = self.game_find_template_match(
                "battle/battle.png",
                threshold=ConfidenceValue("15%"),
                crop_regions=CropRegions(top=0.6, bottom=0.1),
            )
            
            if not battle_match:
                logging.info(f"Squad {faction} battle not ready (Battle button not found).")
                continue
            
            battle_btn = battle_match

            logging.info(f"Squad {faction} active. Executing battle loop...")
            self._run_battle()
            self.sleep_navigation()
