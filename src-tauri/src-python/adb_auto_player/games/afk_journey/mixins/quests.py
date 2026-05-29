"""AFK Journey Quest Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.games.afk_journey.minigames.matching_cards import MatchingCards
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point

_GENERIC_HOLD_CENTER_TOLERANCE = 50


class QuestMixin(AFKJourneyBase, ABC):
    """Assist Mixin."""

    @register_command(
        name="RunQuests",
        gui=GUIMetadata(
            label="Auto-Progress Quests",
            category=AFKJCategory.EVENTS_AND_OTHER,
            tooltip=(
                "Automatically progress and complete available main and side quests"
            ),
        ),
    )
    @register_custom_routine_choice(label="Auto-Progress Quests")
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

            if self.find_any_template(["quests/match_quest"]) is not None:
                logging.info("Matching Cards minigame detected — running automatically")
                try:
                    MatchingCards.matching_cards(self)
                    count = 0
                except Exception as e:
                    logging.error(f"Matching Cards minigame failed: {e}")
                    break

            quest_blockers = [
                "quests/follow_quest",
                "quests/stealth_quest",
                "quests/sorting_quest",
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
                if self._handle_stuck_state():
                    count = 0

            # Check if we're unstuck and reset count if so
            if self._find_quest_images(path=False) is True:
                count = 0

        logging.info("Finished Quest running")

    def _handle_stuck_state(self) -> bool:
        """Handle the stuck state. Returns True if count should be reset."""
        reset = False

        # Action if we've entered a non-quest dialogue
        farewell = self.game_find_template_match(template="quests/farewell.png")
        if farewell:
            logging.warning("Non-quest dialogue found, clearing")
            self.tap(farewell, scale=True)
            sleep(2)
            # Manually path away from the dialogue
            self.tap(Point(880, 365))
            sleep(2)  # Long wait to path before we check for quest images
            reset = True

        # Check if we're in the world screen
        homestead_button = self.game_find_template_match(
            template="navigation/homestead/homestead_enter.png"
        )

        if not homestead_button:
            # Attempt to close any full screen flavour text
            logging.info("Clearing full screen popup")
            self.tap(Point(550, 1825))
            sleep(2)
            back_arrow = self.game_find_template_match("quests/back_arrow.png")
            if back_arrow:
                logging.info("Tapping back arrow to return to normal screen")
                self.tap(back_arrow)
                sleep(2)
                reset = True

        if homestead_button and not farewell:
            # else try and move a few pixels to retrigger action buttons
            logging.warning("Possibly stuck.. trying to fix")
            self.swipe_down(550, 1500, 1510, 0.1)
            sleep(2)

        return reset

    def _find_quest_images(self, path=True) -> bool:
        """Find and click images relating to quests."""
        buttons = [
            "quests/skip",
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
            "quests/claim",
            "quests/questrewards",
            "quests/tap_to_close",
            "quests/tap_to_close_dark",
            "quests/unlocked",
            "navigation/confirm",
            "back",
        ]

        if self._handle_holding_buttons():
            return True

        # Gesture quest: open the emote menu then click the quest-marked gesture
        gesture_button = self.find_any_template(
            ["quests/gesture_button"],
            threshold=ConfidenceValue("80%"),
        )
        if gesture_button is not None:
            self._handle_gesture_quest(gesture_button)
            return True

        # Check for the big "Track" button (diamond/rombo) with a lower threshold
        # due to its semi-transparent background
        track_button = self.find_any_template(
            ["quests/track"],
            threshold=ConfidenceValue("80%"),
        )
        if track_button is not None:
            logging.info("Tapping Track button")
            self.tap(track_button, scale=True)
            sleep(2)
            return True

        if self._handle_dialogue_buttons(buttons):
            return True

        if self._handle_special_quest_actions():
            return True

        # Finally we click the quest tracker text to auto-path. We return False
        # as we need to increment the counter in case we get stuck clicking it
        questbook_match = self.find_any_template(
            ["quests/questbook"],
            threshold=ConfidenceValue("80%"),
        )
        if path and questbook_match is not None:
            nav_match = self.find_any_template(
                ["quests/quest_nav"],
                threshold=ConfidenceValue("80%"),
            )
            if nav_match is not None:
                logging.info("Auto-pathing")
                self.tap(nav_match, scale=True)
                sleep(5)

        return False

    def _handle_holding_buttons(self) -> bool:
        """Check for buttons on screen that we need to hold down."""
        # When the TAP & HOLD wheel appears, the text label is detectable
        # but the golden Cast button is always at screen center — use fixed coords
        tap_and_hold = self.find_any_template(
            templates=["quests/tap_and_hold", "quests/tap_and_hold_large"],
        )
        if tap_and_hold is not None:
            logging.info("TAP & HOLD button detected — holding at button position")
            cast_point = Point(tap_and_hold.x, tap_and_hold.y)
            self.device.swipe(cast_point, cast_point, duration=3.0)
            return True

        # Gesture quest: open the emote menu then click the quest-marked gesture
        gesture_button = self.find_any_template(
            ["quests/gesture_button"],
            threshold=ConfidenceValue("80%"),
        )
        if gesture_button is not None:
            self._handle_gesture_quest(gesture_button)
            return True

        holding_buttons = [
            "quests/sense",
            "quests/heal",
            "quests/place",
            "quests/remove",
            "quests/rewind",
            "quests/cast",
            "quests/cast_alt",
            "quests/cast_alt_v2",
            "quests/feed",
            "quests/encourage",
            "quests/contact",
            "quests/generic_hold",
        ]

        # Check for buttons on screen that we need to hold down
        result = self.find_any_template(
            templates=holding_buttons,
        )
        if result is not None:
            hold_point = Point(result.x, result.y)
            # generic_hold matches the dark wheel navigation arrows which surround
            # the TAP & HOLD wheel. If detected off-center it's a wheel arrow,
            # not the actual hold target — redirect to the wheel's cast button center
            if (
                result.template == "quests/generic_hold"
                and abs(result.x - 540) > _GENERIC_HOLD_CENTER_TOLERANCE
            ):
                hold_point = Point(540, result.y + 170)
            logging.info(
                "Holding button: "
                + result.template.split("/")[-1].replace("_", " ").capitalize()
            )
            self.device.swipe(hold_point, hold_point, duration=3.0)
            return True

        return False

    def _handle_dialogue_buttons(self, buttons: list[str]) -> bool:
        """Click the highest-priority dialogue or action button on screen."""
        # Prioritise checkmarked dialogue choices over generic red dialogue
        checkmark = self.find_any_template(
            ["quests/red_dialogue_checkmark"],
            threshold=ConfidenceValue("80%"),
        )
        if checkmark is not None:
            logging.info("Clicking checkmarked dialogue choice")
            self.tap(checkmark, scale=True)
            sleep(1)
            return True

        # Higher threshold as red/blue_dialogue trigger a lot with background noise
        result = self.find_any_template(
            templates=buttons, threshold=ConfidenceValue("92%")
        )
        if result is None:
            return False
        logging.info(
            "Clicking button: "
            + result.template.split("/")[-1].replace("_", " ").capitalize()
        )
        self.tap(result, scale=True)
        if result.template == "quests/start_battle":
            self.handle_popup_messages()
            logging.info("Waiting for battle to finish")
            sleep(30)  # Longer sleep for battle to finish
        elif result.template == "quests/skip":
            # Skipping always needs confirmation so we do it here quickly
            # rather than run the quest button check for the Confirm button
            sleep(1)
            # logging.info('Confirming Skip..')
            self._tap_till_template_disappears(template="navigation/confirm")
        else:
            sleep(1)
        return True

    def _handle_gesture_quest(self, gesture_button) -> None:
        """Open emote menu and click the appropriate quest gesture."""
        if self.find_any_template(
            ["quests/ancestral_sense"],
            threshold=ConfidenceValue("80%"),
            grayscale=True,
        ):
            logging.info("Ancestral Sense quest — opening gesture menu")
            self.tap(gesture_button, scale=True)
            sleep(2)
            magic_tab = self.find_any_template(
                ["quests/gesture_magic_tab"],
                threshold=ConfidenceValue("80%"),
            )
            if magic_tab is not None:
                logging.info("Navigating to Magic tab")
                self.tap(magic_tab, scale=True)
                sleep(1)
            wolf_form = self.find_any_template(
                ["quests/gesture_wolf_form"],
                threshold=ConfidenceValue("80%"),
            )
            if wolf_form is not None:
                logging.info("Clicking Wolf Form gesture")
                self.tap(wolf_form, scale=True)
                sleep(2)
                sense_button = self.find_any_template(
                    ["quests/ancestral_sense_button"],
                    threshold=ConfidenceValue("80%"),
                )
                if sense_button is not None:
                    logging.info("Pressing Ancestral Sense ability button")
                    self.tap(sense_button, scale=True)
                    sleep(2)
            return

        logging.info("Gesture quest — opening emote menu")
        self.tap(gesture_button, scale=True)
        sleep(2)
        quest_gesture = self.find_any_template(
            [
                "quests/gesture_quest_marker_blue",
                "quests/gesture_quest_marker_orange",
            ],
            threshold=ConfidenceValue("80%"),
        )
        if quest_gesture is not None:
            logging.info("Clicking quest gesture")
            self.tap(quest_gesture, scale=True)
            sleep(2)

    def _handle_special_quest_actions(self) -> bool:
        """Handle time-change and outfit-change prompts."""
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

        return False
