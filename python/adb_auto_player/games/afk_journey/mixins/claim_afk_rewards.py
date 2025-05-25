import logging
from time import sleep

from adb_auto_player import Coordinates, CropRegions
from adb_auto_player.decorators.register_custom_routine_choice import (
    register_custom_routine_choice,
)
from adb_auto_player.games.afk_journey.base import AFKJourneyBase


class ClaimAFKRewards(AFKJourneyBase):
    @register_custom_routine_choice("Claim AFK Rewards")
    def _claiming_afk_progress_chest(self) -> None:
        self.start_up(device_streaming=True)
        logging.info("Claiming AFK Rewards.")
        self._navigate_to_afk_stages_screen()

        logging.info("Tapping AFK Rewards chest.")
        for _ in range(3):
            self.tap(Coordinates(x=550, y=1080), scale=True)
            self.tap(Coordinates(x=520, y=1400), scale=True)
            sleep(1)
        sleep(1)
        logging.info("AFK Rewards claimed.")

    # copied from afk_stages.py will refactor later
    def _navigate_to_afk_stages_screen(self) -> None:
        logging.info("Navigating to AFK stages screen.")
        self._navigate_to_default_state()
        self.tap(Coordinates(x=460, y=1830), scale=True)
        x, y = self.wait_for_template("afk_stage.png", threshold=0.75)
        while self.game_find_template_match("afk_stage.png", threshold=0.75):
            self.tap(Coordinates(x, y))
            sleep(2)
        self.wait_for_template(
            template="resonating_hall.png",
            crop=CropRegions(left=0.3, right=0.3, top=0.9),
        )
