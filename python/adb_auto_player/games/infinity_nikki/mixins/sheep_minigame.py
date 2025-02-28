from abc import ABC
from time import sleep
import logging

from adb_auto_player.games.infinity_nikki.base import InfinityNikkiBase


class SheepMinigameMixin(InfinityNikkiBase, ABC):
    def afk_sheep_minigame(self):
        self.start_up(device_streaming=True)

        _ = self.wait_for_template(
            "conversation/history.png",
            timeout=self.FAST_TIMEOUT,
            timeout_message="Talk to the Sheep Minigame person before starting",
        )

        while True:
            if self.find_template_match("conversation/history.png"):
                self.click(1250, 575, scale=True)
            if self.find_template_match("rewards/bling.png", threshold=0.7):
                logging.debug("Bling visible")
                self.click(950, 950, scale=True)
            sleep(0.5)
