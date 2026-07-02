"""Homestead helper mixin."""

import logging
import re
from enum import Enum
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
from adb_auto_player.ocr import RapidOCRBackend
from adb_auto_player.util import SummaryGenerator


class _RequestFulfillment(Enum):
    """Outcome of attempting to fulfill a single homestead request."""

    DELIVERED = "delivered"
    CRAFTED = "crafted"
    NOTHING = "nothing"


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

    # Templates - greyed-out action button (a required ingredient is missing and
    # can itself be crafted). Appears in the centre action-button slot.
    HOMESTEAD_GRAY_ACTION_BUTTON_TEMPLATES: ClassVar[tuple[str, ...]] = (
        "homestead/gray_make_button.png",
        "homestead/gray_alchem_button.png",
        "homestead/gray_forge_button.png",
    )

    # Templates - ingredient crafting screen (reached after tapping the grey
    # action button and following the missing-ingredient popup arrow).
    HOMESTEAD_INGREDIENT_ACTION_BUTTON_TEMPLATES: ClassVar[tuple[str, ...]] = (
        "homestead/ingredient_smelt_button.png",
        "homestead/ingredient_shape_button.png",
        "homestead/ingredient_refine_button.png",
    )
    HOMESTEAD_INGREDIENT_TAP_TO_CLOSE_TEMPLATE = "homestead/ingredient_tap_to_close.png"

    # Fixed tap point for the multiplier button (cycles x1 -> x5 -> x10)
    HOMESTEAD_MULTIPLIER_BUTTON_POINT = Point(760, 1660)
    # Fixed tap point for the action button (Make / Alchemize / Forge)
    HOMESTEAD_ACTION_BUTTON_POINT = Point(540, 1680)
    # Fixed tap point for the greyed-out action button (centre slot).
    HOMESTEAD_GRAY_ACTION_BUTTON_POINT = Point(520, 1675)
    # Fixed tap point for the ingredient crafting action button (Smelt/Shape/...).
    HOMESTEAD_INGREDIENT_ACTION_BUTTON_POINT = Point(631, 1811)
    # Tap point to dismiss the "Tap to close" rewards popup (bottom of screen).
    HOMESTEAD_TAP_TO_CLOSE_POINT = Point(540, 1800)
    # Fixed tap point for the Requests world-icon (always at same position)
    HOMESTEAD_REQUESTS_POINT = Point(60, 1245)

    # The four request NPC portraits at the bottom of the Requests view. Tapping
    # one selects that request and updates the "Basic Rewards" panel at the top.
    HOMESTEAD_REQUEST_PORTRAIT_POINTS: ClassVar[tuple[Point, ...]] = (
        Point(270, 1815),
        Point(452, 1815),
        Point(640, 1815),
        Point(822, 1815),
    )
    # Crop region (x1, y1, x2, y2) of the Wish Point reward number shown under
    # "Basic Rewards" (left reward card) for the currently selected request.
    # The number's vertical position varies (~y=768 for most requests, ~y=819
    # for the request pre-selected when the view opens), so the crop is tall
    # enough to cover both. The x range fits 3-5 digit centre-aligned values
    # while staying clear of the Ancient Coin number on the right card.
    HOMESTEAD_WISH_POINT_CROP: ClassVar[tuple[int, int, int, int]] = (
        190,
        745,
        330,
        850,
    )
    # After selecting a portrait the Basic Rewards panel animates in, so the
    # number is briefly blank. Retry the OCR read a few times until it appears.
    HOMESTEAD_WISH_POINT_READ_ATTEMPTS = 5
    HOMESTEAD_WISH_POINT_READ_DELAY = 0.6

    # Ingredient-crafting slider geometry. The handle starts at the far left
    # (value 0); dragging right increases the craft amount. The track spans
    # roughly x=250..900. We pull ~20% of the way to queue a small batch.
    HOMESTEAD_SLIDER_Y = 1582
    HOMESTEAD_SLIDER_START_X = 245
    HOMESTEAD_SLIDER_END_X = 375

    # Tuning
    HOMESTEAD_MINE_SCROLL_ATTEMPTS = 5
    HOMESTEAD_HARVEST_TIMEOUT = 30
    HOMESTEAD_OUTER_LOOP_LIMIT = 15
    HOMESTEAD_INNER_LOOP_LIMIT = 25
    # Abort ingredient crafting if nothing progresses within this many seconds.
    HOMESTEAD_INGREDIENT_CRAFT_TIMEOUT = 30

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
        """Repeatedly open Requests, pick the best-rewarded order and fulfill it.

        Each time the Requests view is entered, the four request portraits are
        compared by their Wish Point reward and the highest one is selected
        before fulfilling. After a craft trip the view is re-entered and the
        comparison is repeated.
        """
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

            crafted_this_round = self._fulfill_requests_best_first()

            if crafted_this_round:
                # After a crafting trip the bot may still be inside the crafting
                # or requests screen. Navigate back to the homestead world view
                # before the next outer-loop iteration checks for the Requests icon.
                self._ensure_in_homestead()
                continue

            # No missing-resource craft needed - nothing left to do.
            logging.info("No orders remaining - done.")
            self.press_back_button()
            sleep(2)
            return

        logging.info("Homestead requests: reached outer loop limit.")

    def _fulfill_requests_best_first(self) -> bool:
        """Fulfill requests best-first until a craft cycle or exhaustion.

        Each iteration compares the four request portraits by their Wish Point
        reward, selects the highest and fulfills it once. Requests that cannot
        be progressed are skipped for the remainder of this Requests visit.

        Returns:
            True  if a crafting trip was made (caller should re-enter Requests).
            False if nothing more to do in this Requests visit.
        """
        exhausted: set[int] = set()

        for _ in range(self.HOMESTEAD_INNER_LOOP_LIMIT):
            selected = self._select_best_request(exclude=exhausted)
            if selected is None:
                logging.info("No selectable request - no more orders.")
                return False

            result = self._fulfill_selected_request()

            if result is _RequestFulfillment.CRAFTED:
                return True  # caller will call _ensure_in_homestead() then retry
            if result is _RequestFulfillment.NOTHING:
                # This request cannot be progressed right now; skip it and try
                # the next-best one in the following iteration.
                exhausted.add(selected)
            # DELIVERED: loop again and re-compare the remaining requests.

        logging.info("Request fulfillment inner loop limit reached.")
        return False

    def _read_request_wish_points(self, exclude: set[int]) -> dict[int, int]:
        """Tap each request portrait and OCR its Wish Point reward value.

        Args:
            exclude: Portrait indices to skip (already exhausted this visit).

        Returns:
            Mapping of portrait index (0-based) to Wish Point value. Portraits
            in ``exclude`` or whose number could not be read are omitted.
        """
        backend = getattr(self, "_homestead_ocr_backend", None)
        if backend is None:
            backend = RapidOCRBackend()
            self._homestead_ocr_backend = backend

        x1, y1, x2, y2 = self.HOMESTEAD_WISH_POINT_CROP
        values: dict[int, int] = {}
        for index, point in enumerate(self.HOMESTEAD_REQUEST_PORTRAIT_POINTS):
            if index in exclude:
                continue
            self.tap(point)
            # The Basic Rewards panel animates in after selecting a portrait, so
            # the number is briefly blank. Retry until it is readable.
            value: int | None = None
            for _ in range(self.HOMESTEAD_WISH_POINT_READ_ATTEMPTS):
                sleep(self.HOMESTEAD_WISH_POINT_READ_DELAY)
                crop = self.get_screenshot()[y1:y2, x1:x2]
                digits = re.sub(r"\D", "", backend.extract_text(crop))
                if digits:
                    value = int(digits)
                    break
            if value is not None:
                values[index] = value
                logging.debug("Request %d Wish Points: %d", index + 1, value)
            else:
                logging.debug("Request %d Wish Points unreadable.", index + 1)
        return values

    def _select_best_request(self, exclude: set[int]) -> int | None:
        """Select the request with the highest Wish Point reward.

        Reads all four request portraits, taps the one with the highest Wish
        Point value (ignoring any in ``exclude``) and returns its index.

        Args:
            exclude: Portrait indices to skip (already exhausted this visit).

        Returns:
            The selected portrait index, or None if no request could be read.
        """
        candidates = self._read_request_wish_points(exclude=exclude)
        if not candidates:
            logging.info("No selectable requests with a readable reward.")
            return None

        best_index = max(candidates, key=lambda i: candidates[i])
        logging.info(
            "Selecting request %d (Wish Points: %d).",
            best_index + 1,
            candidates[best_index],
        )
        self.tap(self.HOMESTEAD_REQUEST_PORTRAIT_POINTS[best_index])
        sleep(1.5)  # let the selection settle before Quick Select
        return best_index

    def _fulfill_selected_request(self) -> _RequestFulfillment:
        """Fulfill the currently selected request once via Quick Select.

        Taps Quick Select and then either crafts a missing resource or delivers
        the order. Exactly one Quick Select action is handled so the caller can
        re-compare request rewards afterwards.

        Returns:
            CRAFTED  if a craft trip was started (caller should re-enter).
            DELIVERED if an order was delivered.
            NOTHING  if there was nothing to do for this request.
        """
        quick_select = self.game_find_template_match(
            template=self.HOMESTEAD_QUICK_SELECT_TEMPLATE
        )
        if quick_select is None:
            logging.info("Quick Select not visible for this request.")
            return _RequestFulfillment.NOTHING

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
            return _RequestFulfillment.CRAFTED

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
            SummaryGenerator.increment("Homestead Orders Helper", "Orders Delivered")
            return _RequestFulfillment.DELIVERED

        # Nothing matched for this request.
        logging.debug("No Deliver or missing-resource popup found for this request.")
        return _RequestFulfillment.NOTHING

    # ------------------------------------------------------------------ #
    #  Crafting multiplier                                                 #
    # ------------------------------------------------------------------ #

    def _handle_crafting_to_max(self) -> None:
        """Wait for crafting screen, cycle multiplier to x10, press action button.

        If the action button is greyed out, a required ingredient is missing and
        must be crafted first. In that case we follow the missing-ingredient
        popup into the ingredient crafting screen, craft a small batch, and
        return — the caller will re-enter the original craft afterwards.

        Raises:
            GameTimeoutError: if the crafting screen never loads or crafting
                does not complete within the timeout — the caller should stop
                the mode rather than loop indefinitely.
        """
        action_templates = list(self.HOMESTEAD_ACTION_BUTTON_TEMPLATES)
        gray_templates = list(self.HOMESTEAD_GRAY_ACTION_BUTTON_TEMPLATES)

        logging.info("Waiting for crafting screen to load...")
        # The action button may be coloured (ready) or grey (ingredient missing).
        result = self.wait_for_any_template(
            templates=action_templates + gray_templates,
            timeout=30,
        )

        sleep(2)  # let the UI fully settle

        # A grey action button means a required ingredient is missing but can be
        # crafted. Handle that sub-flow and bail out of the normal craft path.
        if result.template in gray_templates:
            logging.info(
                "Greyed-out action button detected - a required ingredient is "
                "missing. Navigating to ingredient crafting."
            )
            self._handle_missing_ingredient_craft()
            return

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
        # to reappear — that signals crafting is complete. Once a batch is
        # crafted a previously available ingredient may run out, so the button
        # can come back greyed-out instead of coloured.
        sleep(5)
        logging.info("Waiting for crafting to complete...")
        result = self.wait_for_any_template(
            templates=action_templates + gray_templates,
            timeout=30,
        )

        SummaryGenerator.increment("Homestead Orders Helper", "Items Crafted")
        logging.info("Crafting done.")

        # Crafting consumed the last of an ingredient: the button is now grey.
        # Craft the missing ingredient before returning to the caller.
        if result.template in gray_templates:
            logging.info(
                "Action button greyed-out after crafting - a required "
                "ingredient ran out. Navigating to ingredient crafting."
            )
            self._handle_missing_ingredient_craft()

    # ------------------------------------------------------------------ #
    #  Missing-ingredient crafting                                         #
    # ------------------------------------------------------------------ #

    def _handle_missing_ingredient_craft(self) -> None:
        """Craft a missing ingredient via the grey action-button sub-flow.

        Flow:
            1. Tap the grey action button -> a popup like the missing-resource
               one appears; tap its arrow to navigate to ingredient crafting.
            2. On the ingredient crafting screen, drag the amount slider ~20%
               to the right and press the green action button (Smelt/Shape/...).
            3. A "Tap to close" rewards popup appears; tap the bottom of the
               screen to dismiss it.
            4. Press back to return to the homestead world view.

        If nothing progresses within ``HOMESTEAD_INGREDIENT_CRAFT_TIMEOUT``
        seconds the sub-flow is aborted and we simply press back so the caller
        can recover.
        """
        # Tap the grey action button to open the missing-ingredient popup.
        logging.info("Tapping greyed-out action button.")
        self.tap(self.HOMESTEAD_GRAY_ACTION_BUTTON_POINT)
        sleep(2)

        # The popup mirrors the missing-resource one: tap its arrow to navigate.
        arrow = self.game_find_template_match(
            template=self.HOMESTEAD_MISSING_RESOURCES_TEMPLATE
        )
        if arrow is not None:
            logging.info("Tapping popup arrow to navigate to ingredient crafting.")
            self.tap(arrow)
        else:
            logging.warning(
                "Missing-ingredient popup arrow not found - aborting ingredient craft."
            )
            self.press_back_button()
            sleep(2)
            return

        # Wait for the ingredient crafting screen (its green action button).
        ingredient_buttons = list(self.HOMESTEAD_INGREDIENT_ACTION_BUTTON_TEMPLATES)
        try:
            self.wait_for_any_template(
                templates=ingredient_buttons,
                timeout=self.HOMESTEAD_INGREDIENT_CRAFT_TIMEOUT,
                timeout_message="Ingredient crafting screen did not load.",
            )
        except GameTimeoutError:
            logging.warning(
                "Ingredient crafting screen did not load within %ds - aborting.",
                self.HOMESTEAD_INGREDIENT_CRAFT_TIMEOUT,
            )
            self.press_back_button()
            sleep(2)
            return

        sleep(1.5)  # let the screen settle before grabbing the slider

        # Drag the amount slider ~20% to the right (from 0).
        logging.info("Dragging amount slider to the right.")
        self.device.swipe(
            Point(self.HOMESTEAD_SLIDER_START_X, self.HOMESTEAD_SLIDER_Y),
            Point(self.HOMESTEAD_SLIDER_END_X, self.HOMESTEAD_SLIDER_Y),
            duration=0.6,
        )
        sleep(1.5)

        # Press the green action button (Smelt / Shape / Refine).
        logging.info("Pressing ingredient craft button.")
        self.tap(self.HOMESTEAD_INGREDIENT_ACTION_BUTTON_POINT)

        # Wait for the "Tap to close" rewards popup, then dismiss it.
        try:
            self.wait_for_template(
                template=self.HOMESTEAD_INGREDIENT_TAP_TO_CLOSE_TEMPLATE,
                threshold=ConfidenceValue("60%"),
                grayscale=True,
                timeout=self.HOMESTEAD_INGREDIENT_CRAFT_TIMEOUT,
                timeout_message="Ingredient craft did not complete.",
            )
        except GameTimeoutError:
            logging.warning(
                "Ingredient craft did not complete within %ds - aborting.",
                self.HOMESTEAD_INGREDIENT_CRAFT_TIMEOUT,
            )
            self.press_back_button()
            sleep(2)
            return

        logging.info("Dismissing 'Tap to close' popup.")
        self.tap(self.HOMESTEAD_TAP_TO_CLOSE_POINT)
        sleep(2)

        SummaryGenerator.increment("Homestead Orders Helper", "Ingredients Crafted")

        # Navigate back to the homestead world view.
        logging.info("Returning from ingredient crafting.")
        self.press_back_button()
        sleep(2)
