"""Homestead helper mixin."""

import logging
import re
from collections.abc import Callable
from time import sleep

import cv2
from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.image_manipulation import Color, ColorFormat
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Offset, Point
from adb_auto_player.ocr import PSM, TesseractBackend, TesseractConfig
from adb_auto_player.util import SummaryGenerator


class HomesteadHelperMixin(AFKJourneyBase):
    """Homestead helper mixin."""

    # Navigation points.
    HOMESTEAD_BUILDINGS_SECTION_POINT = Point(680, 415)
    PRODUCTION_BUILDING_ENTRY_POINT = Point(630, 1780)
    PRODUCTION_SCREEN_POINT = Point(535, 1220)

    # Crafting controls.
    CRAFT_ITEM_POINT = Point(530, 1700)
    SELECT_ITEM_OFFSET = Offset(0, 345)
    CRAFTING_REQUESTS_INITIAL_WAIT = 7
    CRAFTING_STOCK_SLICE = (923, 915, 80, 50)
    CRAFTING_REQUEST_SLICE = (953, 975, 50, 50)

    # Order selling controls.
    ORDER_COMPLETE_MAIN_OFFSET = Offset(-50, 50)
    ORDER_COMPLETE_OFFSET = Offset(-50, 75)
    ORDER_SELL_POINT = Point(620, 1620)
    POPUP_DISMISS_POINT = Point(540, 1800)

    @register_command(
        name="HomesteadOrdersHelper",
        gui=GUIMetadata(
            label="Homestead Orders Helper",
            category=AFKJCategory.GAME_MODES,
        ),
    )
    def navigate_production_buildings_for_crafting(self) -> None:
        """Navigate through kitchen, forge, and alchemy for crafting."""
        self.start_up()
        logging.warning(
            "This will try to handle all scenarios but you are recommended to put your"
            " production buildings horizontally (at least not adjacent to each other)"
        )
        self.navigate_to_homestead()
        crafted_count = 0
        building_templates = [
            "homestead/navigate_to_kitchen.png",
            "homestead/navigate_to_forge.png",
            "homestead/navigate_to_alchemy.png",
        ]

        while True:
            self.navigate_to_homestead_overview()
            for building_template in building_templates:
                remaining_crafts = (
                    self.settings.homestead.craft_item_limit - crafted_count
                )
                if remaining_crafts <= 0:
                    logging.info("Craft item limit reached: %s", crafted_count)
                    self.navigate_to_homestead()
                    return
                self.navigate_to_production_building(
                    building_template,
                    from_overview=True,
                )
                crafted, limit_reached = self._handle_crafting_requests(
                    remaining_crafts=remaining_crafts,
                )
                crafted_count += crafted
                if limit_reached:
                    logging.info("Craft item limit reached: %s", crafted_count)
                    self.navigate_to_homestead()
                    return
            self.navigate_to_homestead()
            sold_count = self._handle_order_selling()
            if sold_count:
                self.navigate_to_homestead()

    def navigate_to_homestead_overview(self) -> None:
        """Navigate to the Homestead overview screen."""
        logging.info("Navigating to Homestead overview...")
        self._with_retries(
            action=self._open_homestead_overview,
            failure_log="Failed to reach Homestead overview, retrying navigation.",
        )
        self._enter_production_buildings_section()

    def navigate_to_production_building(
        self,
        building_template: str,
        *,
        from_overview: bool = False,
    ) -> None:
        """Navigate to a specific production building."""
        if not from_overview:
            self.navigate_to_homestead_overview()

        building_button = self.wait_for_template(
            template=building_template,
            timeout=self.NAVIGATION_TIMEOUT,
            timeout_message=(
                f"Failed to find production building button: {building_template}"
            ),
        )
        self.tap(building_button)
        sleep(2)
        # Static UI: these fixed taps replace navigate_to_kitchen/forge/alchemy flow.
        self.tap(self.PRODUCTION_BUILDING_ENTRY_POINT)
        sleep(15)
        self.tap(self.PRODUCTION_SCREEN_POINT)
        sleep(3)

    ############################## Helper Functions ##############################

    def _with_retries(
        self,
        *,
        action: Callable[[], None],
        failure_log: str,
        retries: int = 3,
        on_retry: Callable[[], None] | None = None,
    ) -> None:
        """Retry wrapper for navigation steps."""
        attempt = 0
        while True:
            attempt += 1
            try:
                action()
                return
            except GameTimeoutError:
                if attempt >= retries:
                    raise
                logging.warning(failure_log)
                if on_retry is not None:
                    on_retry()
                sleep(2)

    def _open_homestead_overview(self) -> None:
        """Open the Homestead overview using the overview button."""
        sleep(2)  # allow UI to settle before matching
        overview_check = self.wait_for_template(
            template="homestead/homestead_overview_check.png",
            timeout=self.NAVIGATION_TIMEOUT,
            timeout_message="Failed to find Homestead overview button.",
        )
        self.tap(overview_check)
        sleep(2)

    def _enter_production_buildings_section(self) -> None:
        """Enter the production buildings section from overview."""
        # Enter buildings from overview (tap fixed coordinates).
        self.tap(self.HOMESTEAD_BUILDINGS_SECTION_POINT)
        sleep(2)

        def open_production() -> None:
            production_button = self.wait_for_template(
                template="homestead/homestead_overview_production.png",
                timeout=self.NAVIGATION_TIMEOUT,
                timeout_message="Failed to find Homestead production button.",
            )
            self.tap(production_button)
            sleep(2)

        self._with_retries(
            action=open_production,
            failure_log="Failed to enter production buildings, retrying from overview.",
            on_retry=lambda: (
                self.tap(self.HOMESTEAD_BUILDINGS_SECTION_POINT),
                sleep(2),
            ),
        )

    def _handle_crafting_requests(
        self,
        *,
        remaining_crafts: int | None = None,
    ) -> tuple[int, bool]:
        """Handle crafting requests inside a production building.

        Returns:
            tuple[int, bool]: Crafted count and whether the craft limit was hit.
        """
        crafted = 0
        ocr = TesseractBackend(config=TesseractConfig(psm=PSM.SINGLE_LINE))
        while True:
            request_icon = self.game_find_template_match(
                template="homestead/requests.png",
            )
            if request_icon is None:
                self._return_to_production_building_selection()
                return crafted, False

            request_target = request_icon.box.center + self.SELECT_ITEM_OFFSET
            self.tap(request_target)
            sleep(4)

            stock_count, request_count = self._get_crafting_counts(ocr)
            if stock_count is None or request_count is None:
                logging.warning(
                    "OCR failed for crafting counts (stock=%s, request=%s); skipping.",
                    stock_count,
                    request_count,
                )
                self._return_to_requests_list()
                continue

            needed = request_count - stock_count
            if needed <= 0:
                self._return_to_requests_list()
                continue

            if remaining_crafts is not None:
                remaining = remaining_crafts - crafted
                if remaining <= 0:
                    return crafted, True
                needed = min(needed, remaining)

            for _ in range(needed):
                self.tap(self.CRAFT_ITEM_POINT)
                self._wait_for_crafting_deck()
                crafted += 1
                SummaryGenerator.increment("Homestead Orders Helper", "Items Crafted")
                if remaining_crafts is None:
                    limit_reached = False
                else:
                    limit_reached = crafted >= remaining_crafts
                if limit_reached:
                    return crafted, True
            self._return_to_requests_list()

    def _return_to_production_building_selection(self) -> None:
        """Return to the production building selection screen."""
        self.navigate_to_homestead()
        self.navigate_to_homestead_overview()

    def _wait_for_crafting_deck(
        self,
        *,
        initial_wait: int | None = None,
    ) -> None:
        """Wait for crafting deck after starting a craft."""
        initial_wait = (
            self.CRAFTING_REQUESTS_INITIAL_WAIT
            if initial_wait is None
            else initial_wait
        )
        sleep(initial_wait)

        while True:
            if self.game_find_template_match(
                template="homestead/deck_in_crafting_page.png",
            ):
                return
            sleep(3)

    def _return_to_requests_list(self) -> None:
        self.press_back_button()
        sleep(4)
        self.press_back_button()
        sleep(4)

    def _get_crafting_counts(
        self,
        ocr: TesseractBackend,
    ) -> tuple[int | None, int | None]:
        screenshot = self.get_screenshot()
        stock_count = self._ocr_number_from_slice(
            screenshot,
            self.CRAFTING_STOCK_SLICE,
            ocr,
        )
        request_count = self._ocr_number_from_slice(
            screenshot,
            self.CRAFTING_REQUEST_SLICE,
            ocr,
        )
        return stock_count, request_count

    def _ocr_number_from_slice(
        self,
        image,
        region: tuple[int, int, int, int],
        ocr: TesseractBackend,
    ) -> int | None:
        x, y, width, height = region
        crop = image[y : y + height, x : x + width]
        if crop.size == 0:
            return None
        gray = Color.to_grayscale(crop, ColorFormat.BGR)
        _, thresholded = cv2.threshold(
            gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU
        )
        text = ocr.extract_text(thresholded)
        digits = re.findall(r"\d+", text)
        if not digits:
            return None
        return int("".join(digits))

    def _handle_order_selling(self) -> int:
        """Sell completed orders from the main page."""
        order_complete = self.game_find_template_match(
            template="homestead/order_complete_main_page.png",
        )
        if order_complete is None:
            return 0

        self.tap(order_complete.box.center + self.ORDER_COMPLETE_MAIN_OFFSET)
        sleep(2)
        return self._sell_completed_orders()

    def _sell_completed_orders(self) -> int:
        """Sell all completed orders on the orders page."""
        sold_count = 0
        while True:
            order_complete = self.game_find_template_match(
                template="homestead/order_complete.png",
            )
            if order_complete is None:
                break
            self.tap(order_complete.box.center + self.ORDER_COMPLETE_OFFSET)
            sleep(4)
            self.tap(self.ORDER_SELL_POINT)
            sleep(4)
            self.tap(self.ORDER_SELL_POINT)
            sleep(4)
            if not self.handle_popup_messages():
                self.tap(self.POPUP_DISMISS_POINT)
                sleep(4)
            sold_count += 1
            SummaryGenerator.increment("Homestead Orders Helper", "Orders Sold")
        return sold_count
