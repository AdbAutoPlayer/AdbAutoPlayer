"""AFK Journey Assist Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.game import Game
from adb_auto_player.games.afk_journey.afkjourneynavigation import (
    AFKJourneyNavigation as Navigation,
)
from adb_auto_player.games.afk_journey.base import AFKJourneyBase as Base
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions

_WORLD_CHAT_POINT = Point(110, 350)


class AssistMixin(Base, ABC):
    """Assist Mixin."""

    @register_command(
        name="AssistSynergyAndCC",
        gui=GUIMetadata(
            label="Synergy & CC",
            category=AFKJCategory.EVENTS_AND_OTHER,
        ),
    )
    def assist_synergy_corrupt_creature(self) -> None:
        """Assist Synergy and Corrupt Creature."""
        # TODO this needs to be refactored
        # because the chat window can be moved
        # the crop region for "assist/empty_chat.png"
        # needs to be dynamically derived based on the location from the world chat
        # or tap to enter labels
        self.start_up()

        if self._stream is None:
            logging.warning(
                "This feature is quite slow without Device Streaming "
                "you will miss a lot of Synergy and CC requests"
            )

        assist_limit = Base.get_config(self).general.assist_limit
        logging.info("Searching Synergy & Corrupt Creature requests in World Chat")
        count: int = 0
        while count < assist_limit:
            if self._find_synergy_or_corrupt_creature():
                count += 1
                logging.info(f"Assist #{count}")

        logging.info("Finished: Synergy & CC")

    def _find_synergy_or_corrupt_creature(self) -> bool:  # noqa: PLR0911 - TODO
        """Find Synergy or Corrupt Creature."""
        result = Game.find_any_template(
            self,
            templates=[
                "assist/label_world_chat.png",
                "assist/tap_to_enter.png",
                "assist/label_team-up_chat.png",
            ],
        )
        if result is None:
            logging.info("Navigating to World Chat")
            Navigation.navigate_to_default_state(self)
            Game.tap(self, Point(1010, 1080), scale=True)
            sleep(1)
            Game.tap(self, _WORLD_CHAT_POINT, scale=True)
            return False

        match result.template:
            # Chat Window is open but not on World Chat
            case "assist/tap_to_enter.png" | "assist/label_team-up_chat.png":
                logging.info("Switching to World Chat")
                Game.tap(self, _WORLD_CHAT_POINT, scale=True)
                return False
            case "assist/label_world_chat.png":
                pass

        profile_icon = Game.find_worst_match(
            self,
            "assist/empty_chat.png",
            crop_regions=CropRegions(left=0.2, right=0.7, top=0.7, bottom=0.22),
        )

        if profile_icon is None:
            sleep(1)
            return False

        Game.tap(self, profile_icon)
        try:
            result = Game.wait_for_any_template(
                self,
                templates=[
                    "assist/join_now.png",
                    "assist/synergy.png",
                    "assist/chat_button.png",
                ],
                crop_regions=CropRegions(left=0.1, top=0.4, bottom=0.1),
                delay=0.1,
                timeout=self.FAST_TIMEOUT,
            )
        except GameTimeoutError:
            return False
        if result.template == "assist/chat_button.png":
            if (
                Game.game_find_template_match(
                    self, template="assist/label_world_chat.png"
                )
                is None
            ):
                # Back button does not always close profile/chat windows
                Game.tap(self, Point(550, 100), scale=True)
                sleep(1)
            return False
        Game.tap(self, result)
        match result.template:
            case "assist/join_now.png":
                logging.info("Clicking Corrupt Creature join now button")
                try:
                    return self._handle_corrupt_creature()
                except GameTimeoutError:
                    logging.warning(
                        "Clicked join now button too late or something went wrong"
                    )
                    return False
            case "assist/synergy.png":
                logging.info("Clicking Synergy button")
                return self._handle_synergy()
        return False

    def _handle_corrupt_creature(self) -> bool:
        """Handle Corrupt Creature."""
        ready = Game.wait_for_template(
            self,
            template="assist/ready.png",
            crop_regions=CropRegions(left=0.2, right=0.1, top=0.8),
            timeout=self.MIN_TIMEOUT,
        )

        while Game.game_find_template_match(
            self,
            template="assist/ready.png",
            crop_regions=CropRegions(left=0.2, right=0.1, top=0.8),
        ):
            Game.tap(self, ready)
            sleep(0.5)

        while True:
            result = Game.wait_for_any_template(
                self,
                templates=[
                    "assist/bell.png",
                    "guide/close.png",
                    "guide/next.png",
                    "assist/label_world_chat.png",
                    "navigation/time_of_day.png",
                ],
                timeout=self.BATTLE_TIMEOUT,
            )
            logging.debug(f"template {result.template}")
            match result.template:
                case "assist/bell.png":
                    sleep(2)
                    break
                case "guide/close.png" | "guide/next.png":
                    self._handle_guide_popup()
                case _:
                    logging.debug("false")
                    logging.debug(f"template {result.template}")

                    return False

        logging.debug("Placing heroes")
        # click first 5 heroes in row 1 and 2
        for x in [110, 290, 470, 630, 800]:
            Game.tap(self, Point(x, 1300), scale=True)
            sleep(0.5)
        while True:
            cc_ready = Game.game_find_template_match(
                self,
                template="assist/cc_ready.png",
            )
            if cc_ready:
                Game.tap(self, cc_ready)
                sleep(1)
            else:
                break
        Game.wait_for_template(
            self,
            template="assist/reward.png",
            crop_regions=CropRegions(left=0.3, right=0.3, top=0.6, bottom=0.3),
        )
        logging.info("Corrupt Creature done")
        Game.press_back_button(self)
        return True

    def _handle_synergy(self) -> bool:
        """Handle Synergy."""
        go = Game.game_find_template_match(
            self,
            template="assist/go.png",
        )
        if go is None:
            logging.info("Clicked Synergy button too late")
            return False
        Game.tap(self, go)
        sleep(3)
        Game.tap(self, Point(130, 900), scale=True)
        sleep(1)
        Game.tap(self, Point(630, 1800), scale=True)
        logging.info("Synergy complete")
        return True
