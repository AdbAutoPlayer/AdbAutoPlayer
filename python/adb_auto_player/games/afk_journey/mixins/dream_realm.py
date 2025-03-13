"""Dream Realm Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player import Coordinates, GameTimeoutError
from adb_auto_player.games.afk_journey import AFKJourneyBase


class DreamRealmMixin(AFKJourneyBase, ABC):
    """Dream Realm Mixin."""

    def __init__(self) -> None:
        """Initialize DreamRealmMixin."""
        super().__init__()
        # Battle and Skip buttons are in the same coordinates.
        self.battle_skip_coor = Coordinates(550, 1790)

    def run_dream_realm(self) -> None:
        """Use Dream Realm attempts."""
        self.start_up()
        paid_attempts: bool = self.get_config().dream_realm.spend_gold

        self._enter_dr()

        while self._stop_condition(paid_attempts):
            self._start_dr()

    ############################## Helper Functions ##############################

    def _start_dr(self) -> None:
        """Start Dream Realm battle."""
        # No logging because spam from trival method.
        self.click(self.battle_skip_coor)
        sleep(2)

    def _stop_condition(self, spend_gold: bool = False) -> bool:
        """Determine whether to continue with Dream Realm battles.

        Args:
            spend_gold (bool, optional): Buy DR attempts. Defaults to False.

        Returns:
            bool: True if we have attempts to use, False otherwise.
        """
        logging.debug("Check stop condition.")
        no_attempts: tuple[int, int] | None = self.game_find_template_match(
            "dream_realm/done.png"
        )

        if not no_attempts:
            return True

        logging.debug("Free DR attempts used.")
        if not spend_gold:
            logging.info("Not spending gold. Dream Realm finished.")
            return False

        return self._attempt_purchase()

    def _attempt_purchase(self) -> bool:
        """Try to purchase a Dream Realm attempt.

        Returns:
            bool: True if a purchase was made, False if no attempt could be purchased.
        """
        buy: tuple[int, int] | None = self.game_find_template_match(
            "dream_realm/buy.png"
        )

        if buy:
            logging.debug("Purchasing DR attempt.")
            self.click(Coordinates(*buy))
            return True

        logging.debug("Looking for more DR attempts...")
        self.click(self.battle_skip_coor)

        try:
            buy = self.wait_for_template(template="dream_realm/buy.png", timeout=3)
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
        dr_mode: tuple[int, int] = self.wait_for_template(
            "dream_realm/label.png",
            timeout_message="Could not find Dream Realm.",
            timeout=self.MIN_TIMEOUT,
        )
        self.click(Coordinates(*dr_mode))
        sleep(2)
