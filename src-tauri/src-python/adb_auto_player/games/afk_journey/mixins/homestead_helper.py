"""Homestead helper mixin."""

import logging
from collections.abc import Callable
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Offset, Point


class HomesteadHelperMixin(AFKJourneyBase):
    """Homestead helper mixin."""

    # Homestead overview + production navigation coordinates.
    HOMESTEAD_BUILDINGS_SECTION_POINT = Point(680, 415)
    PRODUCTION_BUILDING_ENTRY_POINT = Point(630, 1780)
    PRODUCTION_SCREEN_POINT = Point(535, 1220)
    CRAFT_ITEM_POINT = Point(530, 1700)
    SELECT_ITEM_OFFSET = Offset(0, 345)
    CRAFTING_REQUESTS_INITIAL_WAIT = 7
    ORDER_COMPLETE_MAIN_OFFSET = Offset(-50, 50)
    ORDER_COMPLETE_OFFSET = Offset(-50, 75)
    ORDER_SELL_POINT = Point(620, 1620)
    POPUP_DISMISS_POINT = Point(540, 1800)

    def navigate_to_homestead_overview(self) -> None:
        """Navigate to the Homestead overview screen."""
        logging.info("Navigating to Homestead overview.")
        self._with_retries(
            action=self._open_homestead_overview,
            failure_log="Failed to reach Homestead overview, retrying navigation.",
        )
        self._enter_production_buildings_section()

    @register_command(
        name="HomesteadOrdersHelper",
        gui=GUIMetadata(
            label="Homestead Orders Helper",
            category=AFKJCategory.WIP_PLEASE_TEST,
        ),
    )
    def navigate_production_buildings_for_crafting(self) -> None:
        """Navigate through kitchen, forge, and alchemy for crafting."""
        self.start_up()
        self.navigate_to_homestead()
        building_templates = [
            "homestead/navigate_to_kitchen.png",
            "homestead/navigate_to_forge.png",
            "homestead/navigate_to_alchemy.png",
        ]

        while True:
            for building_template in building_templates:
                self.navigate_to_homestead_overview()
                self.navigate_to_production_building(
                    building_template,
                    from_overview=True,
                )
                self._handle_crafting_requests()
            self._handle_order_selling()

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

    def _handle_crafting_requests(self) -> None:
        """Handle crafting requests inside a production building."""
        while True:
            request_icon = self.game_find_template_match(
                template="homestead/requests.png",
            )
            if request_icon is None:
                if self._return_to_crafting_screen():
                    continue
                self._return_to_homestead_overview()
                return
                self._return_to_homestead_overview()
                return

            request_target = request_icon.box.center + self.SELECT_ITEM_OFFSET
            self.tap(request_target)
            sleep(4)

            try:
                _ = self.wait_for_template(
                    template="homestead/go_to_requests.png",
                    timeout=15,
                )
                self.press_back_button()
                sleep(2)
                self._return_to_crafting_screen()
            except GameTimeoutError:
                self.tap(self.CRAFT_ITEM_POINT)
                if self._wait_for_crafting_deck_or_requests():
                    self.press_back_button()
                    sleep(2)
                    self._return_to_crafting_screen()

    def _open_homestead_overview(self) -> None:
        """Open the Homestead overview using the overview button."""
        self.start_up()
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

    def _return_to_homestead_overview(self) -> None:
        """Press back until the Homestead overview entry is visible."""
        max_back_presses = 8
        for _ in range(max_back_presses):
            if self.game_find_template_match(
                template="homestead/homestead_overview_check.png",
            ):
                return
            if self.game_find_template_match(
                template="homestead/homestead_overview_production.png",
            ):
                return
            self.press_back_button()
            sleep(2)
            try:
                _ = self.wait_for_template(
                    template="homestead/homestead_overview_check.png",
                    timeout=6,
                )
                return
            except GameTimeoutError:
                continue
        logging.warning("Failed to return to Homestead overview after back presses.")

    def _wait_for_crafting_deck_or_requests(
        self,
        *,
        initial_wait: int | None = None,
    ) -> bool:
        """Wait for crafting deck or go_to_requests after starting a craft.

        Returns:
            bool: True if go_to_requests appears, False if deck is back.
        """
        initial_wait = (
            self.CRAFTING_REQUESTS_INITIAL_WAIT
            if initial_wait is None
            else initial_wait
        )
        waited = 0
        while waited < initial_wait:
            if self.game_find_template_match(
                template="homestead/go_to_requests.png",
            ):
                return True
            sleep(2)
            waited += 2

        while True:
            if self.game_find_template_match(
                template="homestead/go_to_requests.png",
            ):
                return True
            if self.game_find_template_match(
                template="homestead/deck_in_crafting_page.png",
            ):
                return False
            sleep(3)

    def _handle_order_selling(self) -> None:
        """Sell completed orders from the main page."""
        order_complete = self.game_find_template_match(
            template="homestead/order_complete_main_page.png",
        )
        if order_complete is None:
            return

        self.tap(order_complete.box.center + self.ORDER_COMPLETE_MAIN_OFFSET)
        sleep(2)
        self._sell_completed_orders()
        self._return_to_homestead_overview()

    def _sell_completed_orders(self) -> None:
        """Sell all completed orders on the orders page."""
        while True:
            order_complete = self.game_find_template_match(
                template="homestead/order_complete.png",
            )
            if order_complete is None:
                break
            self.tap(order_complete.box.center + self.ORDER_COMPLETE_OFFSET)
            sleep(2)
            self.tap(self.ORDER_SELL_POINT)
            sleep(4)
            if not self.handle_popup_messages():
                self.tap(self.POPUP_DISMISS_POINT)
                sleep(2)

    def _return_to_crafting_screen(self) -> bool:
        """Ensure we are back on the crafting screen with requests visible."""
        attempts = 0
        max_attempts = 3
        while attempts < max_attempts:
            try:
                _ = self.wait_for_template(
                    template="homestead/requests.png",
                    timeout=3,
                )
                return True
            except GameTimeoutError:
                self.press_back_button()
                sleep(2)
                attempts += 1
        return False

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
