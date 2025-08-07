import logging
from time import sleep

from adb_auto_player.decorators import (
    register_custom_routine_choice,
)
from adb_auto_player.models.geometry import Point

from ..base import AFKJourneyBase


class ClaimAFKRewards(AFKJourneyBase):
    @register_custom_routine_choice("Claim AFK Rewards")
    def _claiming_afk_progress_chest(self) -> None:
        self.start_up()
        logging.info("Claiming AFK Rewards.")
        self.navigate_to_afk_stages_screen()

        logging.info("Tapping AFK Rewards chest.")
        for _ in range(3):
            self.tap(Point(x=520, y=1400), scale=True, log_message=None)
            self.tap(Point(x=550, y=1080), scale=True, log_message=None)
            sleep(1)
        sleep(1)
        # Make sure the Popup doesn't block collecting AFK Rewards
        self.tap(Point(x=550, y=1080), scale=True, log_message=None)
        if self.get_config().claim_afk_rewards:
            for _ in range(3):
                self.tap(Point(x=770, y=500), scale=True, log_message=None)
                self.tap(Point(x=770, y=500), scale=True, log_message=None)
                sleep(1)
            sleep(1)
        logging.info("AFK Rewards claimed.")
