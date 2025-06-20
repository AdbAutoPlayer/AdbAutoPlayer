"""AFK Journey Assist Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player import GameTimeoutError
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions


class AssistMixin(AFKJourneyBase, ABC):
    """Assist Mixin."""

    @register_command(
        name="AssistSynergyAndCC",
        gui=GuiMetadata(
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

        assist_limit = self.get_config().general.assist_limit
        logging.info("Searching Synergy & Corrupt Creature requests in World Chat")
        count: int = 0
        while count < assist_limit:
            if self._find_synergy_or_corrupt_creature():
                count += 1
                logging.info(f"Assist #{count}")

        logging.info("Finished: Synergy & CC")

    def _find_synergy_or_corrupt_creature(self) -> bool:  # noqa: PLR0911 - TODO
        """Find Synergy or Corrupt Creature."""
        result: tuple[str, int, int] | None = self.find_any_template(
            templates=[
                "assist/label_world_chat.png",
                "assist/tap_to_enter.png",
                "assist/label_team-up_chat.png",
            ],
        )
        if result is None:
            logging.info("Navigating to World Chat")
            self.navigate_to_default_state()
            self.tap(Point(1010, 1080), scale=True)
            sleep(1)
            self.tap(Point(110, 350), scale=True)
            return False

        template, x, y = result
        match template:
            # Chat Window is open but not on World Chat
            case "assist/tap_to_enter.png", "assist/label_team-up_chat.png":
                logging.info("Switching to World Chat")
                self.tap(Point(110, 350), scale=True)
                return False
            case "assist/label_world_chat.png":
                pass

        profile_icon = self.find_worst_match(
            "assist/empty_chat.png",
            crop_regions=CropRegions(left=0.2, right=0.7, top=0.7, bottom=0.22),
        )

        if profile_icon is None:
            sleep(1)
            return False

        self.tap(Point(*profile_icon))
        try:
            template, x, y = self.wait_for_any_template(
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
        if template == "assist/chat_button.png":
            if (
                self.game_find_template_match(
                    template="assist/label_world_chat.png",
                )
                is None
            ):
                # Back button does not always close profile/chat windows
                self.tap(Point(550, 100), scale=True)
                sleep(1)
            return False
        self.tap(Point(x, y))
        match template:
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
        ready: tuple[int, int] = self.wait_for_template(
            template="assist/ready.png",
            crop_regions=CropRegions(left=0.2, right=0.1, top=0.8),
            timeout=self.MIN_TIMEOUT,
        )

        while self.game_find_template_match(
            template="assist/ready.png",
            crop_regions=CropRegions(left=0.2, right=0.1, top=0.8),
        ):
            self.tap(Point(*ready))
            sleep(0.5)

        while True:
            template, _, _ = self.wait_for_any_template(
                templates=[
                    "assist/bell.png",
                    "guide/close.png",
                    "guide/next.png",
                    "assist/label_world_chat.png",
                    "navigation/time_of_day.png",
                ],
                timeout=self.BATTLE_TIMEOUT,
            )
            logging.debug(f"template {template}")
            match template:
                case "assist/bell.png":
                    sleep(2)
                    break
                case "guide/close.png" | "guide/next.png":
                    self._handle_guide_popup()
                case _:
                    logging.debug("false")
                    logging.debug(f"template {template}")

                    return False

        logging.debug("Placing heroes")
        # click first 5 heroes in row 1 and 2
        for x in [110, 290, 470, 630, 800]:
            self.tap(Point(x, 1300), scale=True)
            sleep(0.5)
        while True:
            cc_ready: tuple[int, int] | None = self.game_find_template_match(
                template="assist/cc_ready.png",
            )
            if cc_ready:
                self.tap(Point(*cc_ready))
                sleep(1)
            else:
                break
        self.wait_for_template(
            template="assist/reward.png",
            crop_regions=CropRegions(left=0.3, right=0.3, top=0.6, bottom=0.3),
        )
        logging.info("Corrupt Creature done")
        self.press_back_button()
        return True

    def _handle_synergy(self) -> bool:
        """Handle Synergy."""
        go: tuple[int, int] | None = self.game_find_template_match(
            template="assist/go.png",
        )
        if go is None:
            logging.info("Clicked Synergy button too late")
            return False
        self.tap(Point(*go))
        sleep(3)
        self.tap(Point(130, 900), scale=True)
        sleep(1)
        self.tap(Point(630, 1800), scale=True)
        logging.info("Synergy complete")
        return True
