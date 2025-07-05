"""Dream Realm Mixin."""

import logging
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.game import Game
from adb_auto_player.games.afk_journey.afkjourneynavigation import (
    AFKJourneyNavigation as Navigation,
)
from adb_auto_player.games.afk_journey.base import AFKJourneyBase as Base
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point


class DreamRealmMixin(Base):
    """Dream Realm Mixin."""

    def __init__(self) -> None:
        """Initialize DreamRealmMixin."""
        super().__init__()
        # Battle and Skip buttons are in the same coordinates.
        self.battle_skip_coord = Point(550, 1790)

    @register_command(
        name="DreamRealm",
        gui=GUIMetadata(
            label="Dream Realm",
            category=AFKJCategory.GAME_MODES,
        ),
    )
    def run_dream_realm(self, daily: bool = False) -> None:
        """Use Dream Realm attempts."""
        self.start_up(device_streaming=False)
        paid_attempts: bool = Base.get_config(self).dream_realm.spend_gold

        try:
            self._enter_dr()
        except GameTimeoutError:
            return

        if daily:
            self._claim_reward()

        while self._stop_condition(paid_attempts, daily):
            self._start_dr()

        logging.info("Dream Realm finished.")

    ############################## Helper Functions ##############################

    def _start_dr(self) -> None:
        """Start Dream Realm battle."""
        # No logging because spam from trival method.
        Game.tap(self, self.battle_skip_coord)
        sleep(2)

    def _stop_condition(self, spend_gold: bool, daily: bool) -> bool:
        """Determine whether to continue with Dream Realm battles.

        Args:
            spend_gold (bool, optional): Buy DR attempts. Defaults to False.
            daily (bool, optional): Daily run. Defaults to False.

        Returns:
            bool: True if we have attempts to use, False otherwise.
        """
        logging.debug("Check stop condition.")
        no_attempts = Game.game_find_template_match(self, "dream_realm/done.png")

        if (
            daily
            and Game.game_find_template_match(self, "dream_realm/daily_done.png")
            is not None
        ):
            logging.info("Daily Dream Realm battle finished.")
            return False

        if not no_attempts:
            return True

        logging.debug("Free DR attempts used.")
        if not spend_gold:
            logging.info("Not spending gold.")
            return False

        return self._attempt_purchase()

    def _attempt_purchase(self) -> bool:
        """Try to purchase a Dream Realm attempt.

        Returns:
            bool: True if a purchase was made, False if no attempt could be purchased.
        """
        # TODO: Can use _click_confirm_on_popup instead.
        buy = Game.game_find_template_match(self, "dream_realm/buy.png")

        if buy:
            logging.debug("Purchasing DR attempt.")
            Game.tap(self, buy)
            return True

        logging.debug("Looking for more DR attempts...")
        Game.tap(self, self.battle_skip_coord)

        try:
            buy = Game.wait_for_template(
                self, template="dream_realm/buy.png", timeout=self.FAST_TIMEOUT
            )
            logging.debug("Purchasing DR attempt.")
            Game.tap(self, buy)
            return True
        except GameTimeoutError:
            logging.info("No more DR attempts to purchase.")
            return False

    def _enter_dr(self) -> None:
        """Enter Dream Realm."""
        logging.info("Entering Dream Realm...")
        Navigation.navigate_to_default_state(self)
        Game.tap(self, Point(460, 1830))  # Battle Modes
        try:
            dr_mode = Game.wait_for_template(
                self,
                "dream_realm/label.png",
                timeout_message="Could not find Dream Realm.",
                timeout=self.MIN_TIMEOUT,
            )
            Game.tap(self, dr_mode)
            sleep(2)
        except GameTimeoutError as fail:
            logging.error(f"{fail} {self.LANG_ERROR}")
            raise

    def _claim_reward(self) -> None:
        """Claim Dream Realm reward."""
        logging.debug("Claim yesterday's rewards.")
        reward = Game.game_find_template_match(self, "dream_realm/dr_ranking.png")

        if not reward:
            logging.debug("Failed to find rankings.")
            return

        Game.tap(self, reward)
        sleep(2)

        try:
            logging.debug("Click Tap to Close, if available.")
            tap_to_close = Game.wait_for_template(
                self,
                "tap_to_close.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="Dream Realm rewards already claimed.",
            )
            Game.tap(self, tap_to_close)
            sleep(1)
        except GameTimeoutError as fail:
            logging.info(fail)

        logging.debug("Return to Dream Realm.")
        Game.press_back_button(self)
        sleep(4)
