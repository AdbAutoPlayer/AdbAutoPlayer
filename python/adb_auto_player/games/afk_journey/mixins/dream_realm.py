"""Dream Realm Mixin."""

import logging
from time import sleep

from adb_auto_player import Coordinates, GameTimeoutError
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory


class DreamRealmMixin(AFKJourneyBase):
    """Dream Realm Mixin."""

    def __init__(self) -> None:
        """Initialize DreamRealmMixin."""
        super().__init__()
        # Battle and Skip buttons are in the same coordinates.
        self.battle_skip_coord = Coordinates(550, 1790)

    @register_command(
        name="DreamRealm",
        gui=GuiMetadata(
            label="Dream Realm",
            category=AFKJCategory.GAME_MODES,
        ),
    )
    def run_dream_realm(self, daily: bool = False) -> None:
        """Use Dream Realm attempts."""
        self.start_up()
        paid_attempts: bool = self.get_config().dream_realm.spend_gold

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
        self.click(self.battle_skip_coord)
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
        no_attempts: tuple[int, int] | None = self.game_find_template_match(
            "dream_realm/done.png"
        )

        if (
            daily
            and self.game_find_template_match("dream_realm/daily_done.png") is not None
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
        buy: tuple[int, int] | None = self.game_find_template_match(
            "dream_realm/buy.png"
        )

        if buy:
            logging.debug("Purchasing DR attempt.")
            self.click(Coordinates(*buy))
            return True

        logging.debug("Looking for more DR attempts...")
        self.click(self.battle_skip_coord)

        try:
            buy = self.wait_for_template(
                template="dream_realm/buy.png", timeout=self.FAST_TIMEOUT
            )
            logging.debug("Purchasing DR attempt.")
            self.click(Coordinates(*buy))
            return True
        except GameTimeoutError:
            logging.info("No more DR attempts to purchase.")
            return False

    def _enter_dr(self) -> None:
        """Enter Dream Realm."""
        logging.info("Entering Dream Realm...")
        self._navigate_to_default_state()
        self.click(Coordinates(460, 1830))  # Battle Modes
        try:
            dr_mode: tuple[int, int] = self.wait_for_template(
                "dream_realm/label.png",
                timeout_message="Could not find Dream Realm.",
                timeout=self.MIN_TIMEOUT,
            )
            self.click(Coordinates(*dr_mode))
            sleep(2)
        except GameTimeoutError as fail:
            logging.error(f"{fail} {self.LANG_ERROR}")
            raise

    def _claim_reward(self) -> None:
        """Claim Dream Realm reward."""
        logging.debug("Claim yesterday's rewards.")
        reward: tuple[int, int] | None = self.game_find_template_match(
            "dream_realm/dr_ranking.png"
        )

        if not reward:
            logging.debug("Failed to find rankings.")
            return

        self.click(Coordinates(*reward))
        sleep(2)

        try:
            logging.debug("Click Tap to Close, if available.")
            tap_to_close: tuple[int, int] = self.wait_for_template(
                "tap_to_close.png",
                timeout=self.FAST_TIMEOUT,
                timeout_message="Dream Realm rewards already claimed.",
            )
            self.click(Coordinates(*tap_to_close))
            sleep(1)
        except GameTimeoutError as fail:
            logging.info(fail)

        logging.debug("Return to Dream Realm.")
        self.press_back_button()
        sleep(4)
