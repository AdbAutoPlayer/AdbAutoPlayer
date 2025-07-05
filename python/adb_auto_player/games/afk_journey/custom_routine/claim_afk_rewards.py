import logging
from time import sleep

from adb_auto_player.decorators import (
    register_custom_routine_choice,
)
from adb_auto_player.game import Game
from adb_auto_player.games.afk_journey.afkjourneynavigation import (
    AFKJourneyNavigation as Navigation,
)
from adb_auto_player.models.geometry import Point

from ..base import AFKJourneyBase as Base


class ClaimAFKRewards(Base):
    @register_custom_routine_choice("Claim AFK Rewards")
    def _claiming_afk_progress_chest(self) -> None:
        self.start_up()
        logging.info("Claiming AFK Rewards.")
        Navigation.navigate_to_afk_stages_screen(self)

        logging.info("Tapping AFK Rewards chest.")
        for _ in range(3):
            Game.tap(self, Point(x=550, y=1080), scale=True, log_message=None)
            Game.tap(self, Point(x=520, y=1400), scale=True, log_message=None)
            sleep(1)
        sleep(1)
        if Base.get_config(self).claim_afk_rewards:
            for _ in range(3):
                Game.tap(self, Point(x=770, y=500), scale=True, log_message=None)
                Game.tap(self, Point(x=770, y=500), scale=True, log_message=None)
                sleep(1)
            sleep(1)
        logging.info("AFK Rewards claimed.")
