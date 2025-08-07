"""AFK Journey Assist Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import TemplateMatchResult


class AssistMixin(AFKJourneyBase, ABC):
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
        self.start_up()

        if self._stream is None:
            logging.warning(
                "This feature is quite slow without Device Streaming "
                "you will miss a lot of Synergy and CC requests"
            )

        logging.info("Searching Synergy & Corrupt Creature requests in World Chat")
        count: int = 0
        while count < self.get_config().general.assist_limit:
            if self._find_synergy_or_corrupt_creature():
                count += 1
                logging.info(f"Assist #{count}")

        logging.info("Finished: Synergy & CC")

    def _open_chat(self) -> None:
        logging.info("Opening Chat")
        self.navigate_to_default_state()
        self.device.press_enter()
        sleep(2)

    def _find_profile_icon(self, world_chat_label: Box) -> TemplateMatchResult | None:
        crop_left = world_chat_label.top_left.x
        crop_top = world_chat_label.top_left.y + 990

        return self.find_worst_match(
            "assist/empty_chat.png",
            crop_regions=CropRegions(
                left=str(crop_left) + "px",
                right=str(1080 - crop_left - 130) + "px",
                top=str(crop_top) + "px",
                bottom=str(1920 - 250 - crop_top) + "px",
            ),
        )

    def _find_synergy_or_corrupt_creature(self) -> bool:  # noqa: PLR0911 - TODO
        """Find Synergy or Corrupt Creature."""
        result = self.game_find_template_match(
            "assist/label_world_chat.png",
            crop_regions=CropRegions(bottom="50%", right="50%", left="10%"),
        )
        if result is None:
            self._open_chat()
            return False

        profile_icon = self.find_worst_match(
            "assist/empty_chat.png",
            crop_regions=CropRegions(left=0.2, right=0.7, top=0.7, bottom=0.22),
        )

        if profile_icon is None:
            sleep(1)
            return False

        self.tap(profile_icon)
        try:
            result = self.wait_for_any_template(
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
                self.game_find_template_match(
                    template="assist/label_world_chat.png",
                )
                is None
            ):
                # Back button does not always close profile/chat windows
                self.tap(Point(550, 100), scale=True)
                sleep(1)
            return False
        self.tap(result)
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
        ready = self.wait_for_template(
            template="assist/ready.png",
            crop_regions=CropRegions(left=0.2, right=0.1, top=0.8),
            timeout=self.MIN_TIMEOUT,
        )

        while self.game_find_template_match(
            template="assist/ready.png",
            crop_regions=CropRegions(left=0.2, right=0.1, top=0.8),
        ):
            self.tap(ready)
            sleep(0.5)

        while True:
            result = self.wait_for_any_template(
                templates=[
                    "assist/bell.png",
                    "guide/close.png",
                    "guide/next.png",
                    "assist/label_world_chat.png",
                    "navigation/time_of_day.png",
                ],
                timeout=self.BATTLE_TIMEOUT,
            )
            match result.template:
                case "assist/bell.png":
                    sleep(2)
                    break
                case "guide/close.png" | "guide/next.png":
                    self._handle_guide_popup()
                case _:
                    return False

        # click first 5 heroes in row 1 and 2
        for x in [110, 290, 470, 630, 800]:
            self.tap(Point(x, 1300), scale=True)
            sleep(0.5)
        while True:
            cc_ready = self.game_find_template_match(
                template="assist/cc_ready.png",
            )
            if cc_ready:
                self.tap(cc_ready)
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
        go = self.game_find_template_match(
            template="assist/go.png",
        )
        if go is None:
            logging.info("Clicked Synergy button too late")
            return False
        self.tap(go)
        sleep(3)
        self.tap(Point(130, 900), scale=True)
        sleep(1)
        self.tap(Point(630, 1800), scale=True)
        logging.info("Synergy complete")
        return True
