"""AFK Journey Quest Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point


class QuestMixin(AFKJourneyBase, ABC):
    """Assist Mixin."""

    @register_command(
        name="RunQuests",
        gui=GUIMetadata(
            label="Run Available Quests",
            category=AFKJCategory.EVENTS_AND_OTHER,
        ),
    )
    def attempt_quests(self) -> None:
        """Attempt to run quests in quest log."""
        # Basic function to press buttons needed to progress quests, will stop when it
        # hits an unknown button or game mode encounter
        self.start_up()
        timeout_limit = 5  # Exit if no found actions are found this many times

        logging.info("Attempting to run quests!")
        logging.warning(
            "This will try to handle all scenarios but any herding, fetching, "
            "following, mini-games, stealth maps etc will cause it to time-out. "
            "Handle them manually and restart the function"
        )
        count: int = 0
        while count <= timeout_limit:
            if self._find_quest_images() is True:
                count = 0
            else:
                count += 1
                sleep(1)

            quest_blockers = [
                "quests/follow_quest",
                "quests/stealth_quest",
                "quests/sorting_quest",
                "quests/match_quest",
                "quests/locked_quest",
                "quests/pattern_quest",
            ]

            blocked = self.find_any_template(
                templates=quest_blockers,
            )
            if blocked is not None:
                logging.error("Non-automatable quest found: " + blocked.template)
                break

            # Sometimes autopathing multiple times disables the action button when you
            # are stood next to it, moving a few pixels re-enables them
            # Only trigger if we can't see any non-autopathing images
            stuck_cap = 3

            if count >= stuck_cap and self._find_quest_images(path=False) is False:
                # Action if we've entered a non-quest dialogue
                farewell = self.game_find_template_match(template="quests/farewell.png")
                if farewell:
                    logging.warning("Non-quest dialogue found, clearing")
                    self.tap(farewell, scale=True)
                    sleep(2)
                    # Manually path away from the dialogue
                    self.tap(Point(880, 365))
                    sleep(2)  # Long wait to path before we check for quest images
                    count = 0

                # Check if we're in the world screen
                homestead_button = self.game_find_template_match(
                    template="navigation/homestead/homestead_enter.png"
                )

                if not homestead_button:
                    # Attempt to close any full screen flavour text
                    logging.info("Clearing full screen popup")
                    self.tap(Point(550, 1825))
                    sleep(2)

                if homestead_button and not farewell:
                    # else try and move a few pixels to retrigger action buttons
                    logging.warning("Possibly stuck.. trying to fix")
                    self.swipe_down(550, 1500, 1510, 0.1)
                    sleep(2)

            # Check if we're unstuck and reset count if so
            if self._find_quest_images(path=False) is True:
                count = 0

        logging.info("Finished Quest running")

    def _find_quest_images(self, path=True) -> bool:
        """Find and click images relating to quests."""
        buttons = [
            "confirm_text",
            "quests/red_dialogue",
            "quests/blue_dialogue",
            "quests/destiny_dialogue",
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
            "quests/track",
            "back",
        ]

        holding_buttons = [
            "quests/generic_hold",
            "quests/tap_and_hold",
            "quests/tap_and_hold_large",
            "quests/sense",
            "quests/heal",
            "quests/place",
            "quests/remove",
            "quests/rewind",
            "quests/cast",
            "quests/cast_alt",
            "quests/feed",
            "quests/encourage",
            "quests/contact",
        ]

        # First we check for buttons on screen taht we need to hold down
        result = self.find_any_template(
            templates=holding_buttons,
        )
        if result is not None:
            logging.info(
                "Holding button: "
                + result.template.split("/")[-1].replace("_", " ").capitalize()
            )
            self.hold(Point(550, 1200))
            return True

        # Then we check for buttons we need to press, higher threshold as
        # red/blue_dialogue trigger a lot with background noise
        result2 = self.find_any_template(
            templates=buttons, threshold=ConfidenceValue("92%")
        )
        if result2 is not None:
            logging.info(
                "Clicking button: "
                + result2.template.split("/")[-1].replace("_", " ").capitalize()
            )
            self.tap(result2, scale=True)
            if result2.template == "quests/start_battle":
                logging.info("Waiting for battle to finish")
                sleep(30)  # Longer sleep for battle to finish
            elif result2.template == "quests/skip":
                # Skipping always needs confirmation so we do it here quickly
                # rather than run the quest button check for the Confirm button
                sleep(1)
                # logging.info('Confirming Skip..')
                self._tap_till_template_disappears(template="navigation/confirm")
            else:
                sleep(1)
            return True

        if self.find_any_template(["quests/time_change"]):
            logging.info("Changing time")
            self.tap(Point(550, 1500))
            return True

        if self.find_any_template(["confirm_text_italic"]):
            logging.info("Changing outfit")
            self.tap(Point(730, 1800))

            confirm = self.game_find_template_match(template="navigation/confirm")
            if confirm:
                self.tap(confirm)
                sleep(2)
                self.tap(Point(100, 1800))
                sleep(2)
            return True

        # Finally we click the 'Echoes of Dissent' text to auto-path. We return False
        # as we need to increment the counter in case we get stuck clicking it
        if path:
            if self.find_any_template(["quests/questbook"]):
                logging.info("Auto-pathing")
                self.tap(Point(820, 375))
                sleep(5)
                return False

        return False
