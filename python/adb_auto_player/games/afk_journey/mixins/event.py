import logging
from abc import ABC
from time import sleep
from typing import NoReturn

from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class EventMixin(AFKJourneyBase, ABC):
    def event_guild_chat_claim(self) -> NoReturn:
        self.start_up()
        logging.info("This claims rewards in Guild Chat (e.g. Happy Satchel)")
        logging.info("Opening chat")
        self._navigate_to_default_state()
        self.click(1010, 1080, scale=True)
        sleep(3)
        while True:
            claim_button = self.find_template_match(
                "event/guild_chat_claim/claim_button.png"
            )
            if claim_button:
                self.click(*claim_button)
                # click again to close popup
                sleep(2)
                self.click(*claim_button)
            # switch to world chat and back because sometimes chat stops scrolling
            world_chat_icon = self.find_template_match(
                "event/guild_chat_claim/world_chat_icon.png"
            )
            if world_chat_icon:
                self.click(*world_chat_icon)
                sleep(1)
            guild_chat_icon = self.find_template_match(
                "event/guild_chat_claim/guild_chat_icon.png"
            )
            if guild_chat_icon:
                self.click(*guild_chat_icon)
            sleep(1)

    def event_monopoly_assist(self) -> NoReturn:
        self.start_up()
        logging.info("This assists friends on Monopoly board events to farm Pal-Coins")
        logging.warning("You have to open the Monopoly assists screen yourself")
        win_count = 0
        loss_count = 0
        while True:
            self.wait_for_template(
                "event/monopoly_assist/log.png",
                timeout=self.MIN_TIMEOUT,
                timeout_message="Monopoly assists screen not found",
            )

            next_assist: tuple[int, int] | None = None
            count = 0
            while next_assist is None:
                assists = self.find_all_template_matches(
                    "event/monopoly_assist/assists.png"
                )
                for assist in assists:
                    if count >= loss_count:
                        next_assist = assist
                        break
                    count += 1
                if next_assist is None:
                    self.swipe_down()

            self.click(*next_assist)
            sleep(3)
            try:
                if self._handle_battle_screen(use_suggested_formations=False):
                    win_count += 1
                    logging.info(f"Win #{win_count} Pal-Coins: {win_count * 15}")
                else:
                    loss_count += 1
                    logging.warning(f"Loss #{loss_count}")
            except Exception as e:
                logging.error(f"{e}")
