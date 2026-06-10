"""Homestead helper mixin."""

import logging
from time import sleep
from typing import ClassVar

from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.util import SummaryGenerator


class HomesteadHelperMixin(AFKJourneyBase):
    """Homestead helper mixin."""

    # Templates - resource collection
    HOMESTEAD_OVERVIEW_CHECK_TEMPLATE = "homestead/homestead_overview_check.png"
    HOMESTEAD_BUILDINGS_TAB_TEMPLATE = "homestead/buildings_tab.png"
    HOMESTEAD_MINE_TEMPLATE = "homestead/mine_building.png"
    HOMESTEAD_MINE_GO_TEMPLATE = "homestead/mine_go_button.png"
    HOMESTEAD_HARVEST_ALL_TEMPLATE = "homestead/harvest_all.png"

    # Templates - orders / requests
    HOMESTEAD_REQUESTS_TEMPLATE = "homestead/requests_label.png"
    HOMESTEAD_QUICK_SELECT_TEMPLATE = "homestead/quick_select.png"
    HOMESTEAD_DELIVER_TEMPLATE = "homestead/deliver_button.png"
    HOMESTEAD_ORDER_COMPLETE_TEMPLATE = "homestead/order_complete.png"
    HOMESTEAD_MISSING_RESOURCES_TEMPLATE = (
        "homestead/missing_item_navigate_to_crafting.png"
    )

    # Templates - crafting multiplier & action
    HOMESTEAD_MULTIPLIER_X10_TEMPLATE = "homestead/multiplier_x10.png"
    HOMESTEAD_MULTIPLIER_STATE_TEMPLATE = "homestead/multiplier_state.png"
    HOMESTEAD_CRAFTING_SCREEN_TEMPLATE = "homestead/crafting_screen_check.png"
    HOMESTEAD_ACTION_BUTTON_TEMPLATES: ClassVar[tuple[str, ...]] = (
        "homestead/cook_button.png",
        "homestead/alchem_button.png",
        "homestead/forge_button.png",
    )

    # Fixed tap point for the multiplier button (cycles x1 -> x5 -> x10)
    HOMESTEAD_MULTIPLIER_BUTTON_POINT = Point(760, 1660)
    # Fixed tap point for the action button (Make / Alchemize / Forge)
    HOMESTEAD_ACTION_BUTTON_POINT = Point(540, 1680)
    # Fixed tap point for the Requests world-icon (always at same position)
    HOMESTEAD_REQUESTS_POINT = Point(60, 1245)

    # Tuning
    HOMESTEAD_MINE_SCROLL_ATTEMPTS = 5
    HOMESTEAD_HARVEST_TIMEOUT = 30
    HOMESTEAD_OUTER_LOOP_LIMIT = 15
    HOMESTEAD_INNER_LOOP_LIMIT = 25

    @register_command(
        name="HomesteadOrdersHelper",
        gui=GUIMetadata(
            label="Homestead Orders Helper",
            category=AFKJCategory.GAME_MODES,
            tooltip="Collect Mine resources and fulfill Requests orders in Homestead",
        ),
    )
    @register_custom_routine_choice(label="Homestead Orders Helper")
    def homestead_orders_helper(self) -> None:
        """Collect Mine resources and fulfill Homestead Requests orders."""
        self.start_up()
        self._ensure_in_homestead()
        self._collect_homestead_resources()
        self._handle_homestead_requests()

    def _ensure_in_homestead(self) -> None:
        """Enter homestead if not already there.

        Uses the stacked-coins icon (top-right) as the definitive signal that
        we are inside homestead. Presses back to escape any open sub-screens
        (crafting, requests, etc.) before trying to enter.
        Raises GameTimeoutError after 10 attempts.
        """
        for attempt in range(10):
            # Already in homestead world view?
            if self.game_find_template_match(
                template=self.HOMESTEAD_OVERVIEW_CHECK_TEMPLATE
            ):
                logging.info("Already in homestead.")
                return

            # Look for the green Homestead enter button (world view, not inside).
            enter = self.find_any_template(
                [
                    "navigation/homestead/homestead_enter.png",
                    "navigation/homestead/homestead_invaded.png",
                ]
            )
            if enter is not None:
                logging.info(
                    "Tapping homestead enter button (attempt %d).", attempt + 1
                )
                self.tap(enter)
                sleep(4)  # wait for homestead to load
                continue

            # We are inside a sub-screen (crafting, requests, etc.).
            # Press back to get closer to the homestead world view.
            # If the exit-homestead dialog appears, dismiss it with Cancel.
            logging.debug(
                "Sub-screen detected (attempt %d) - pressing back.", attempt + 1
            )
            self.press_back_button()
            sleep(2)
            cancel = self.game_find_template_match(template="cancel.png")
            if cancel is not None:
                logging.info("Exit dialog detected - dismissing with Cancel.")
                self.tap(cancel)
                sleep(2)

        raise GameTimeoutError("Could not navigate to homestead after 10 attempts.")

    # ------------------------------------------------------------------ #
    #  Resource collection                                                 #
    # ------------------------------------------------------------------ #

    def _collect_homestead_resources(self) -> None:
        """Open Buildings -> Mine -> Go -> Harvest All."""
        logging.info("Collecting homestead resources...")

        # Open the management panel and navigate to the Buildings tab.
        # The panel may already be open after navigation, so we try to find
        # the Buildings tab first.  If it isn't visible, tap the stacked-coins
        # icon to toggle the panel open and try again (up to 3 times).
        sleep(2)  # let the UI settle after navigate_to_homestead
        buildings_tab = None
        for attempt in range(3):
            buildings_tab = self.game_find_template_match(
                template=self.HOMESTEAD_BUILDINGS_TAB_TEMPLATE
            )
            if buildings_tab is not None:
                break
            # Panel not open yet - find and tap the stacked-coins icon.
            overview_icon = self.game_find_template_match(
                template=self.HOMESTEAD_OVERVIEW_CHECK_TEMPLATE
            )
            if overview_icon is None:
                logging.warning(
                    "Neither Buildings tab nor overview icon found (attempt %d).",
                    attempt + 1,
                )
                sleep(2)
                continue
            logging.info(
                "Tapping stacked-coins icon to open panel (attempt %d).", attempt + 1
            )
            self.tap(overview_icon)
            sleep(3)  # wait for the panel animation to finish

        if buildings_tab is None:
            logging.warning("Could not open the homestead management panel.")
            return

        self.tap(buildings_tab)
        sleep(2)

        # Scroll down until a Mine building card is visible.
        mine = None
        for _ in range(self.HOMESTEAD_MINE_SCROLL_ATTEMPTS):
            mine = self.game_find_template_match(template=self.HOMESTEAD_MINE_TEMPLATE)
            if mine is not None:
                break
            self.swipe_up(x=540, sy=1500, ey=700)
            sleep(1.5)

        if mine is None:
            logging.warning(
                "Mine building not found after scrolling"
                " - skipping resource collection."
            )
            self.press_back_button()
            sleep(1)
            return

        self.tap(mine)
        sleep(2)

        # Press the green "Go" button to navigate to the Mine in the world.
        go_button = self.wait_for_template(
            template=self.HOMESTEAD_MINE_GO_TEMPLATE,
            timeout=self.navigation_timeout,
            timeout_message="Could not find Mine Go button.",
        )
        self.tap(go_button)
        sleep(3)

        # Wait for the Harvest All button and press it.
        # Use a lower threshold and restrict to the left half of the screen
        # where the world-space mine icon always appears.
        harvest_all = self.wait_for_template(
            template=self.HOMESTEAD_HARVEST_ALL_TEMPLATE,
            threshold=ConfidenceValue("70%"),
            grayscale=True,
            crop_regions=CropRegions(right=0.5),
            timeout=self.HOMESTEAD_HARVEST_TIMEOUT,
            timeout_message="Harvest All button not found.",
        )
        self.tap(harvest_all)
        sleep(4)  # wait for harvest animation and camera to settle

        SummaryGenerator.increment("Homestead Orders Helper", "Resources Harvested")
        logging.info("Resources harvested.")

    # ------------------------------------------------------------------ #
    #  Orders / Requests                                                   #
    # ------------------------------------------------------------------ #

    def _handle_homestead_requests(self) -> None:
        """Repeatedly open Requests and use Quick Select to fulfill orders."""
        logging.info("Handling homestead requests...")

        for _outer in range(self.HOMESTEAD_OUTER_LOOP_LIMIT):
            # Verify Requests icon is visible before tapping fixed coordinate.
            requests_visible = self.game_find_template_match(
                template=self.HOMESTEAD_REQUESTS_TEMPLATE,
                threshold=ConfidenceValue("60%"),
                grayscale=True,
                crop_regions=CropRegions(right=0.75, top=0.55),
            )
            if requests_visible is None:
                logging.info("Requests button not visible - done.")
                return

            logging.info("Tapping Requests icon.")
            self.tap(self.HOMESTEAD_REQUESTS_POINT)
            sleep(2)

            crafted_this_round = self._quick_select_loop()

            if crafted_this_round:
                # After a crafting trip the bot may still be inside the crafting
                # or requests screen. Navigate back to the homestead world view
                # before the next outer-loop iteration checks for the Requests icon.
                self._ensure_in_homestead()
                continue

            if not crafted_this_round:
                # No missing-resource craft needed - nothing left to do.
                logging.info("No orders remaining - done.")
                self.press_back_button()
                sleep(2)
                return

        logging.info("Homestead requests: reached outer loop limit.")

    def _quick_select_loop(self) -> bool:
        """Run Quick Select until a missing-resource case triggers a craft cycle.

        Returns:
            True  if a crafting trip was made (caller should re-enter Requests).
            False if nothing more to do in this session.
        """
        for _ in range(self.HOMESTEAD_INNER_LOOP_LIMIT):
            quick_select = self.game_find_template_match(
                template=self.HOMESTEAD_QUICK_SELECT_TEMPLATE
            )
            if quick_select is None:
                logging.info("Quick Select not visible - no more orders.")
                return False

            self.tap(quick_select)
            sleep(2)

            # Check if the insufficient-resources popup appeared.
            missing_arrow = self.game_find_template_match(
                template=self.HOMESTEAD_MISSING_RESOURCES_TEMPLATE
            )
            if missing_arrow is not None:
                logging.info("Insufficient resources - navigating to crafting.")
                self.tap(missing_arrow)
                sleep(2)
                self._handle_crafting_to_max()
                return True  # caller will call _ensure_in_homestead() then retry

            # No missing-resources popup: check for Deliver button.
            deliver = self.game_find_template_match(
                template=self.HOMESTEAD_DELIVER_TEMPLATE
            )
            if deliver is not None:
                logging.info("Deliver button found - tapping.")
                self.tap(deliver)
                sleep(3)  # wait for reward popup to appear
                # Tap the lower half of the screen to dismiss the reward popup.
                self.tap(Point(540, 1400))
                # Wait for Quick Select to reappear.
                try:
                    self.wait_for_template(
                        template=self.HOMESTEAD_QUICK_SELECT_TEMPLATE,
                        timeout=15,
                        timeout_message="Quick Select did not reappear after delivery.",
                    )
                except Exception:
                    logging.warning("Quick Select did not reappear after delivery.")
                SummaryGenerator.increment(
                    "Homestead Orders Helper", "Orders Delivered"
                )
                continue

            # Nothing matched - press back to close any unexpected screen and
            # let the outer loop re-enter Requests.
            logging.debug("No Quick Select, Deliver or missing-resource popup found.")
            return False

        logging.info("Quick Select inner loop limit reached.")
        return False

    # ------------------------------------------------------------------ #
    #  Crafting multiplier                                                 #
    # ------------------------------------------------------------------ #

    def _handle_crafting_to_max(self) -> None:
        """Wait for crafting screen, cycle multiplier to x10, press action button.

        Raises:
            GameTimeoutError: if the crafting screen never loads or crafting
                does not complete within the timeout — the caller should stop
                the mode rather than loop indefinitely.
        """
        action_templates = list(self.HOMESTEAD_ACTION_BUTTON_TEMPLATES)
        logging.info("Waiting for crafting screen to load...")
        self.wait_for_any_template(
            templates=action_templates,
            timeout=30,
        )

        sleep(2)  # let the UI fully settle

        # Cycle x1 -> x5 -> x10 with exactly 2 taps.
        for tap_num in range(2):
            logging.debug("Tapping multiplier button (%d/2).", tap_num + 1)
            self.tap(self.HOMESTEAD_MULTIPLIER_BUTTON_POINT)
            sleep(1.5)

        # Tap the action button (Cook / Alchemize / Forge).
        logging.info("Tapping action button.")
        self.tap(self.HOMESTEAD_ACTION_BUTTON_POINT)

        # The action button is replaced by a different button while crafting.
        # Sleep briefly to let the UI swap, then wait for the action button
        # to reappear — that signals crafting is complete.
        sleep(5)
        logging.info("Waiting for crafting to complete...")
        self.wait_for_any_template(
            templates=action_templates,
            timeout=30,
        )

        SummaryGenerator.increment("Homestead Orders Helper", "Items Crafted")
        logging.info("Crafting done.")
