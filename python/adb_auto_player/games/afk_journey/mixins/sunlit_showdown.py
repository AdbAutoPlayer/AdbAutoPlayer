"""AFK Journey Sunlit Showdown Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point


class SunlitShowdownMixin(AFKJourneyBase, ABC):
    """Sunlit Showdown Mixin."""

    @register_command(
        name="SunlitShowdown",
        gui=GUIMetadata(
            label="Run Sunlit Showdown",
            category=AFKJCategory.EVENTS_AND_OTHER,
        ),
    )
    def attempt_sunlit(self) -> None:
        """Attempt to run Sunlit Showdown Battles."""
        self.start_up()
        self.navigate_to_default_state()

        logging.info("Attempting to run Sunlit Showdown!")
        logging.warning(
            "Very much an alpha function, designed only to clear the shop. "
            "Currently checks for Shakir, Harak, Shemira, Lenya, Sonja, "
            "Vala, Faramor, Sinbad, Berial and Valka, and picks them in that priorty "
            "order as it scrolls down through heroes"
        )

        if self._open_sunlit_showdown() is False:
            return

        while self._handle_battle():
            self._handle_battle()

        logging.info("Sunlit Showdown Finished!")

    def _open_sunlit_showdown(self) -> bool:
        logging.info(
            "Opening Sunlit Showdown",
        )
        self._tap_till_template_disappears(template="navigation/hamburger_menu")
        sleep(2)
        self._tap_till_template_disappears(template="dailies/hamburger/events")
        sleep(2)
        self._tap_till_template_disappears(
            template="event/sunlit_showdown/sunlit_showdown"
        )
        sleep(2)
        self.wait_for_template(template="event/sunlit_showdown/title_s")
        self.tap(Point(650, 1450))  # Join
        sleep(3)
        self.wait_for_template(template="event/sunlit_showdown/title_s")
        self.tap(Point(800, 1800))  # Start/Continue
        sleep(4)
        if self.game_find_template_match(
            template="event/sunlit_showdown/insufficient_resources"
        ):
            logging.warning("Out of Sunlit Showdown tokens!")
            return False
        return True

    def _handle_battle(self) -> bool:
        # Enter hero selection screen
        self.wait_for_template(template="event/sunlit_showdown/quick_select")
        self.tap(Point(800, 1800))  # Continue/Battle
        sleep(2)
        self._tap_till_template_disappears(template="navigation/confirm")  # consumables
        sleep(4)

        # Clear all hero spots
        self.wait_for_template(template="start_battle")
        logging.debug("Clearing heroes")
        self.tap(Point(425, 950))
        sleep(1)
        self.tap(Point(325, 870))
        sleep(1)
        self.tap(Point(175, 870))
        sleep(1)

        # Select 3 new ones from list of heroes
        self._handle_hero_selection()

        # Start Battle
        self._tap_till_template_disappears(template="start_battle")  # Battle
        logging.info("Battling..")
        sleep(3)
        self._tap_till_template_disappears(template="navigation/confirm")  # Confirm
        sleep(15)

        # Handle end result
        if self._handle_battle_result():
            return True
        else:
            return False

    def _handle_hero_selection(self):
        selected_heroes = 0
        hero_slots = 3
        scrolls = 1
        max_scrolls = 5

        heroes = [
            "heroes/shakir_battle",
            "heroes/harak_battle",
            "heroes/shemira_battle",
            "heroes/lenya_battle",
            "heroes/sonja_battle",
            "heroes/vala_battle",
            "heroes/faramor_battle",
            "heroes/natsu_battle",
            "heroes/sinbad_battle",
            "heroes/berial_battle",
            "heroes/valka_battle",
        ]

        # # Reverse list for testing
        # heroes = [
        #     "heroes/silvina_battle",
        #     "heroes/valka_battle",
        #     "heroes/berial_battle",
        #     "heroes/sinbad_battle",
        #     "heroes/natsu_battle",
        #     "heroes/faramor_battle",
        #     "heroes/vala_battle",
        #     "heroes/sonja_battle",
        #     "heroes/lenya_battle",
        #     "heroes/shemira_battle",
        #     "heroes/harak_battle",
        #     "heroes/shakir_battle",
        # ]

        while selected_heroes < hero_slots:
            hero_checker = self.find_any_template(
                templates=heroes,
                threshold=ConfidenceValue(
                    "93%"
                ),  # Else Faramor triggers while already selected
            )
            if hero_checker is not None:
                scrolls = 1
                logging.info(
                    "Selecting "
                    + hero_checker.template.split("/")[1].split("_")[0].capitalize()
                )
                self.tap(hero_checker)
                sleep(1)
                selected_heroes += 1
                # logging.info(selected_heroes)
            elif scrolls <= max_scrolls:
                logging.info(
                    "No listed hero found, scolling down " + str(scrolls) + "/5"
                )
                self.swipe_up(630, 1630, 1340, duration=2)
                sleep(2)
                scrolls += 1
            if scrolls > max_scrolls:
                self.tap(Point(1000, 1625))
                self.tap(Point(715, 1600))
                self.tap(Point(850, 1600))
                self.tap(Point(1000, 1450))
                logging.info("Hero selection reset")
                return

    def _handle_battle_result(self) -> bool:
        result = self.wait_for_any_template(
            templates=["event/sunlit_showdown/victory", "event/sunlit_showdown/defeat"],
            timeout=self.BATTLE_TIMEOUT,
            delay=1.0,
            timeout_message=self.BATTLE_TIMEOUT_ERROR_MESSAGE,
        )

        match result.template:
            case "event/sunlit_showdown/victory":
                logging.info("Victory!")
                self.tap(Point(550, 1800))  # Tap to Close
                sleep(5)
                # If we won the final clear Battle Record and use next token
                if self.game_find_template_match(
                    template="event/sunlit_showdown/battle_record"
                ):
                    self.tap(Point(550, 1800))  # Tap Battle Record
                    sleep(5)
                    self.wait_for_template(template="event/sunlit_showdown/title_s")
                    self.tap(Point(800, 1800))  # Start/Continue
                    if self.game_find_template_match(
                        template="event/sunlit_showdown/insufficient_resources"
                    ):
                        logging.warning("Out of Sunlit Showdown tokens!")
                        return False
                return True

            case "event/sunlit_showdown/defeat":
                logging.warning("Defeat!")
                self.tap(Point(550, 1800))  # Tap to Close
                sleep(5)
                self.tap(Point(550, 1800))  # Tap Battle Record
                sleep(5)
                # Use another token
                self.wait_for_template(template="event/sunlit_showdown/title_s")
                self.tap(Point(800, 1800))  # Start/Continue
                sleep(4)
                if self.game_find_template_match(
                    template="event/sunlit_showdown/insufficient_resources"
                ):
                    logging.warning("Out of Sunlit Showdown tokens!")
                    return False
                return True

        logging.warning("Something went wrong detecting battle results!")
        return False
