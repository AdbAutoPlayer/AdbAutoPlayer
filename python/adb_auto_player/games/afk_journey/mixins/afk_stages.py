import logging
from abc import ABC

from adb_auto_player.exceptions import TimeoutException
from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class AFKStagesMixin(AFKJourneyBase, ABC):
    def push_afk_stages(self, season: bool) -> None:
        """
        Entry for pushing AFK Stages
        :param season: Push Season Stage if True otherwise push regular AFK Stages
        """
        self.start_up()
        self.store[self.STORE_MODE] = self.MODE_AFK_STAGES

        while True:
            self.store[self.STORE_SEASON] = season
            try:
                self.__start_afk_stage()
            except TimeoutException as e:
                logging.warning(f"{e}")
            if self.get_config().afk_stages.push_both_modes:
                self.store[self.STORE_SEASON] = not season
                try:
                    self.__start_afk_stage()
                except TimeoutException as e:
                    logging.warning(f"{e}")
            if not self.get_config().afk_stages.repeat:
                break
        return None

    def __start_afk_stage(self) -> None:
        stages_pushed: int = 0
        stages_name = self.__get_current_afk_stages_name()

        logging.info(f"Pushing: {stages_name}")
        self.__navigate_to_afk_stages_screen()
        while self._handle_battle_screen(
            self.get_config().afk_stages.use_suggested_formations
        ):
            stages_pushed += 1
            logging.info(f"{stages_name} pushed: {stages_pushed}")
        return None

    def __get_current_afk_stages_name(self) -> str:
        season = self.store.get(self.STORE_SEASON, False)
        if season:
            return "Season Talent Stages"
        return "AFK Stages"

    def __navigate_to_afk_stages_screen(self) -> None:
        logging.info("Navigating to default state")
        self._navigate_to_default_state()
        logging.info("Navigating to AFK Stage Battle screen")
        self.click(90, 1830, scale=True)
        self._select_afk_stage()
