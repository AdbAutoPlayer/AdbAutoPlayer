"""Infinity Nikki Sheep Minigame Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player import Coordinates
from adb_auto_player.games.infinity_nikki.base import InfinityNikkiBase


class SheepMinigameMixin(InfinityNikkiBase, ABC):
    """Infinity Nikki Sheep Minigame Mixin."""

    def afk_sheep_minigame(self) -> None:
        """Automate sheep minigame."""
        logging.error("Update 1.4 ruined this :(, sheep no longer move after eating")
        return None
        self.start_up(device_streaming=True)
        config = self.get_config().sheep_minigame_config

        _ = self.wait_for_template(
            "conversation/history.png",
            timeout=self.FAST_TIMEOUT,
            timeout_message="Talk to the Sheep Minigame person before starting",
        )

        # perfect clear gives 1350 bling
        # bling cap is 160k
        # 160000 / 1350 =~ 119
        bling_visible = False
        count = 0
        history_visible_before_bling_count = 0
        bling_cap = 20
        while count < config.runs:
            if self.game_find_template_match("conversation/history.png"):
                history_visible_before_bling_count += 1
                bling_visible = False
                self.click(Coordinates(1250, 575), scale=True)
            if self.game_find_template_match("rewards/bling.png", threshold=0.7):
                history_visible_before_bling_count = 0
                if not bling_visible:
                    count += 1
                    logging.info(f"Minigame clear #{count}")
                    bling_visible = True
                logging.debug("Bling visible")
                self.click(Coordinates(950, 950), scale=True)
            if retry := self.game_find_template_match(
                "minigame/retry.png",
                threshold=0.7,
            ):
                history_visible_before_bling_count = 0
                self.click(Coordinates(*retry))
                confirm = self.wait_for_template(
                    "minigame/confirm.png",
                    timeout=5,
                )
                self.click(Coordinates(*confirm))
            if history_visible_before_bling_count > bling_cap:
                logging.warning("Exiting because Bling cap has been reached.")
                return None
            sleep(0.5)

        logging.info("Done")
