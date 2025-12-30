"""AFK Journey Frostfire Showdown Mixin."""

import logging
from abc import ABC
from time import sleep

from adb_auto_player.decorators import register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point


class FrostfireShowdownMixin(AFKJourneyBase, ABC):
    """Frostfire Showdown Mixin."""

    def __init__(self) -> None:
        """Initialize Frostfire Showdown Mixin."""
        super().__init__()
        self._defeat_counter = 0

    @register_command(
        name="FrostfireShowdown",
        gui=GUIMetadata(
            label="Run Frostfire Showdown",
            category=AFKJCategory.EVENTS_AND_OTHER,
        ),
    )
    def attempt_frostfire(self) -> None:
        """Attempt to run Frostfire Showdown Battles."""
        self.start_up()
        self.navigate_to_world()
        
        # Reset defeat counter at start
        self._defeat_counter = 0

        logging.info("Attempting to run Frostfire Showdown!")
        logging.warning(
            "Very much an alpha function, designed only to clear the shop. "
            "Currently checks for Shakir, Harak, Shemira, Lenya, Sonja, "
            "Vala, Faramor, Sinbad, Berial and Valka, and picks them in that priorty "
            "order as it scrolls down through heroes"
        )

        if self._open_frostfire_showdown() is False:
            return

        while self._handle_battle():
            self._handle_battle()

        logging.info("Frostfire Showdown Finished!")

    def _open_frostfire_showdown(self) -> bool:
        logging.info(
            "Opening Frostfire Showdown",
        )
        self._tap_till_template_disappears(template="navigation/hamburger_menu")
        sleep(2)
        self._tap_till_template_disappears(template="dailies/hamburger/events")
        sleep(2)
        self._tap_till_template_disappears(
            template="event/frostfire_showdown/frostfire_showdown"
        )
        sleep(2)
        self.wait_for_template(template="event/frostfire_showdown/title_s")
        self.tap(Point(650, 1450))  # Join
        sleep(3)
        self.wait_for_template(template="event/frostfire_showdown/title_s")
        self.tap(Point(800, 1800))  # Start/Continue
        sleep(4)
        if self.game_find_template_match(
            template="event/frostfire_showdown/insufficient_resources"
        ):
            logging.warning("Out of Frostfire Showdown tokens!")
            return False
        return True

    def _handle_battle(self) -> bool:
        # Enter hero selection screen
        self.wait_for_template(template="event/frostfire_showdown/quick_select")
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
        max_scrolls = 10

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
                    "No listed hero found, scolling down " + str(scrolls) + "/10"
                )
                self.swipe_up(400, 1630, 1340, duration=2)
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
            templates=["event/frostfire_showdown/victory", "event/frostfire_showdown/defeat"],
            timeout=self.BATTLE_TIMEOUT,
            delay=1.0,
            timeout_message=self.BATTLE_TIMEOUT_ERROR_MESSAGE,
        )

        match result.template:
            case "event/frostfire_showdown/victory":
                logging.info("Victory!")
                # Reset defeat counter on victory
                self._defeat_counter = 0
                self.tap(Point(550, 1800))  # Tap to Close
                sleep(5)
                # If we won the final clear Battle Record and use next token
                if self.game_find_template_match(
                    template="event/frostfire_showdown/battle_record"
                ):
                    self.tap(Point(550, 1800))  # Tap Battle Record
                    sleep(5)
                    self.wait_for_template(template="event/frostfire_showdown/title_s")
                    self.tap(Point(800, 1800))  # Start/Continue
                    if self.game_find_template_match(
                        template="event/frostfire_showdown/insufficient_resources"
                    ):
                        logging.warning("Out of Frostfire Showdown tokens!")
                        return False
                return True

            case "event/frostfire_showdown/defeat":
                self._defeat_counter += 1
                logging.warning(f"Defeat! (Attempt {self._defeat_counter}/3)")
                self.tap(Point(550, 1800))  # Tap to Close
                sleep(5)
                
                # For first 3 defeats, retry with same token (game goes back to battle screen)
                if self._defeat_counter <= 3:
                    logging.info("Retrying battle with same team...")
                    # Game automatically returns to battle selection screen after clicking close
                    return True
                
                # After 3 defeats, view battle record and use a new token
                logging.info("Max retries reached, using a new token...")
                self._defeat_counter = 0  # Reset counter for next token
                self.tap(Point(550, 1800))  # Tap Battle Record
                sleep(5)
                # Use another token
                self.wait_for_template(template="event/frostfire_showdown/title_s")
                self.tap(Point(800, 1800))  # Start/Continue
                sleep(4)
                if self.game_find_template_match(
                    template="event/frostfire_showdown/insufficient_resources"
                ):
                    logging.warning("Out of Frostfire Showdown tokens!")
                    return False
                return True

        logging.warning("Something went wrong detecting battle results!")
        return False
