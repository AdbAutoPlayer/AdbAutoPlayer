"""AFK Journey Quest Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Point


class QuestMixin(AFKJourneyBase, ABC):
    """Assist Mixin."""

    @register_command(
        name="RunQuests",
        gui=GuiMetadata(
            label="Run Available Quests",
            category=AFKJCategory.EVENTS_AND_OTHER,
        ),
    )
    def attempt_quests(self) -> None:
        """Attempt to run quests in quest log."""
        # Basic function to press buttons needed to progress quests, will stop when it
        # hits an unknown button or game mode encounter
        self.start_up()
        timeout_limit = 7  # Exit if no found actions are found this many times

        logging.info("Attempting to run quests!")
        logging.warning(
            "This will try to handle all scenarios but any herding, fetching, "
            "following, mini-games, stealth maps etc will cause it to time-out. "
            "Handle them manually and restart the function"
        )
        count: int = 0
        while count < timeout_limit:
            if self._find_quest_images() is True:
                count = 0
            else:
                count += 1
                sleep(1)

            # Sometimes autopathing multiple times disables the action button when you
            # are stood next to it, so we move a few pixels to re-enable them
            # Only trigger if we can't see any non-pathing images
            soft_stuck_cap = 3
            hard_stuck_cap = 4

            if count > soft_stuck_cap and not self._find_quest_images(path=False):
                logging.info("Possibly stuck, trying to move")
                self.swipe_down(550, 1500, 1510, 0.1)
                sleep(2)
                if count > hard_stuck_cap:
                    logging.info("Possibly really stuck, trying something different")
                    self.tap(Point(550, 1800))

        logging.info("Finished Quest running")

    def _find_quest_images(self, path=True) -> bool:
        """Find and click images relating to quests."""
        buttons = [
            "confirm_text",
            "quests/red_dialogue",
            "quests/blue_dialogue",
            "quests/interact",
            "quests/dialogue",
            "quests/enter",
            "quests/chest",
            "quests/battle_button",
            "quests/start_battle",
            "quests/questrewards",
            "quests/tap_to_close",
            "quests/unlocked",
            "quests/skip",
            "navigation/confirm",
            "back",
        ]

        holding_buttons = ["quests/tap_and_hold", "quests/sense"]

        # First we check for buttons on screen taht we need to hold down
        result = self.find_any_template(
            templates=holding_buttons,
        )
        if result is not None:
            logging.info("Holding button: " + result.template)
            self.hold(Point(550, 1200))
            return True

        # Then we check for buttons we need to press, higher threshold as
        # red/blue_dialogue trigger a lot with background noise
        result2 = self.find_any_template(
            templates=buttons, threshold=ConfidenceValue("92%")
        )
        if result2 is not None:
            logging.info("Clicking button: " + result2.template)
            self.tap(result2, scale=True)
            sleep(
                1
            )  # allows time for update before checking again if a popup is triggered
            return True

        if self.find_any_template(["quests/time_change"]):
            logging.info("Changing time")
            self.tap(Point(550, 1500))
            return True

        # Finally we click the 'Echoes of Dissent' text to auto-path. We return False
        # as we need to increment the counter in case we get stuck clicking it
        if path:
            if self.find_any_template(["quests/eod"]):
                logging.info("Auto-pathing")
                self.tap(Point(820, 375))
                sleep(3)
                return False

        return False
