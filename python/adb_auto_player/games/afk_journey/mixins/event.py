"""AFK Journey Event Mixin."""

import logging
from abc import ABC
from time import sleep
from typing import NoReturn

from adb_auto_player import AutoPlayerWarningError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions


class EventMixin(AFKJourneyBase, ABC):
    """Mixin for events."""

    def event_guild_chat_claim(self) -> NoReturn:
        """Claim rewards from Guild Chat."""
        self.start_up()
        logging.info("This claims rewards in Guild Chat (e.g. Happy Satchel)")
        logging.info("Opening chat")
        self.navigate_to_default_state()
        self.tap(Point(1010, 1080), scale=True)
        sleep(3)
        while True:
            claim_button = self.game_find_template_match(
                template="event/guild_chat_claim/claim_button.png",
                crop_regions=CropRegions(left=0.6, top=0.2, bottom=0.2),
            )
            if claim_button:
                self.tap(claim_button)
                # click again to close popup
                sleep(2)
                self.tap(claim_button)
            # switch to world chat and back because sometimes chat stops scrolling
            world_chat_icon = self.game_find_template_match(
                template="event/guild_chat_claim/world_chat_icon.png",
                crop_regions=CropRegions(right=0.8, top=0.1, bottom=0.3),
            )
            if world_chat_icon:
                self.tap(world_chat_icon)
                sleep(1)
            guild_chat_icon = self.game_find_template_match(
                template="event/guild_chat_claim/guild_chat_icon.png",
                crop_regions=CropRegions(right=0.8, top=0.1, bottom=0.3),
            )
            if guild_chat_icon:
                self.tap(guild_chat_icon)
            sleep(1)

    def event_monopoly_assist(self) -> NoReturn:
        """Farm Pal-Coins from Monopoly assists."""
        self.start_up()
        logging.info("This assists friends on Monopoly board events to farm Pal-Coins")
        logging.warning("You have to open the Monopoly assists screen yourself")
        win_count = 0
        loss_count = 0
        while True:
            self.wait_for_template(
                template="event/monopoly_assist/log.png",
                # TODO cropping next time event shows up
                crop_regions=CropRegions(bottom=0.5),
                timeout=self.MIN_TIMEOUT,
                timeout_message="Monopoly assists screen not found",
            )

            next_assist = None
            count = 0
            while next_assist is None:
                assists = self.find_all_template_matches(
                    "event/monopoly_assist/assists.png",
                    # TODO cropping next time event shows up
                )
                for assist in assists:
                    if count >= loss_count:
                        next_assist = assist
                        break
                    count += 1
                if next_assist is None:
                    self.swipe_up(sy=1350, ey=500)

            self.tap(next_assist)
            sleep(3)
            try:
                if self._handle_battle_screen(use_suggested_formations=False):
                    win_count += 1
                    logging.info(f"Win #{win_count} Pal-Coins: {win_count * 15}")
                else:
                    loss_count += 1
                    logging.warning(f"Loss #{loss_count}")
            except AutoPlayerWarningError as e:
                logging.warning(f"{e}")
            except Exception as e:
                logging.error(f"{e}")
