"""AFK Stages Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player import Coordinates, GameTimeoutError
from adb_auto_player.games.afk_journey import AFKJourneyBase


class AFKStagesMixin(AFKJourneyBase, ABC):
    """AFK Stages Mixin."""

    def push_afk_stages(self, season: bool) -> None:
        """Entry for pushing AFK Stages.

        Args:
            season: Push Season Stage if True otherwise push regular AFK Stages
        """
        self.start_up()
        self.store[self.STORE_MODE] = self.MODE_AFK_STAGES

        while True:
            self.store[self.STORE_SEASON] = season
            try:
                self._start_afk_stage()
            except GameTimeoutError as e:
                logging.warning(f"{e}")
            if self.get_config().afk_stages.push_both_modes:
                self.store[self.STORE_SEASON] = not season
                try:
                    self._start_afk_stage()
                except GameTimeoutError as e:
                    logging.warning(f"{e}")
            if not self.get_config().afk_stages.repeat:
                break

    def _start_afk_stage(self) -> None:
        """Start push."""
        stages_pushed: int = 0
        stages_name = self._get_current_afk_stages_name()

        logging.info(f"Pushing: {stages_name}")
        self._navigate_to_afk_stages_screen()
        while self._handle_battle_screen(
            self.get_config().afk_stages.use_suggested_formations,
            self.get_config().afk_stages.skip_manual_formations,
        ):
            stages_pushed += 1
            logging.info(f"{stages_name} pushed: {stages_pushed}")

    def _get_current_afk_stages_name(self) -> str:
        """Get stage name."""
        season = self.store.get(self.STORE_SEASON, False)
        if season:
            return "Season Talent Stages"
        return "AFK Stages"

    def _navigate_to_afk_stages_screen(self) -> None:
        """Navigate to stages screen."""
        logging.info("Navigating to default state")
        self._navigate_to_default_state()
        logging.info("Clicking Battle Modes button")
        self.click(Coordinates(x=460, y=1830), scale=True)
        x, y = self.wait_for_template("afk_stage.png", threshold=0.75)
        while self.game_find_template_match("afk_stage.png", threshold=0.75):
            self.click(Coordinates(x, y))
            sleep(2)
        self._select_afk_stage()
