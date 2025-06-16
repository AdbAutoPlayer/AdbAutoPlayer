import logging
from time import sleep

from adb_auto_player import Coordinates, CropRegions
from adb_auto_player.decorators.register_custom_routine_choice import (
    register_custom_routine_choice,
)
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.log_presets import LogPreset


class LevelUpAllHeroes(AFKJourneyBase):
    @register_custom_routine_choice("Level Up All Heroes")
    def _level_up_all_heroes(self) -> None:
        self.start_up()
        logging.info("Starting Level Up All Heroes.")
        self.navigate_to_resonating_hall()

        if self._find_level_up_all_button() is None:
            logging.info(
                "Level Up All Heroes not available.",
                extra={"preset": LogPreset.NOT_AVAILABLE},
            )
            return

        logging.info("Clicking Level Up All Heroes.")
        if level_up_all_button := self._find_level_up_all_button():
            for _ in range(3):
                for _ in range(10):
                    self.tap(level_up_all_button, blocking=False, log_message=None)
                sleep(2)
            sleep(3)
        logging.info("Level Up All Heroes completed.")
        return

    def _find_level_up_all_button(self) -> Coordinates | None:
        if level_up_all_button := self.game_find_template_match(
            "resonating_hall/level_up_all.png",
            crop=CropRegions(left=0.3, right=0.3, top=0.7),
            threshold=0.95,
        ):
            return Coordinates(*level_up_all_button)
        return None
