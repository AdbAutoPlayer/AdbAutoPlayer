import logging
from abc import ABC
from time import sleep
from typing import NoReturn

from adb_auto_player.exceptions import TimeoutException
from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class ArcaneLabyrinthMixin(AFKJourneyBase, ABC):
    def handle_arcane_labyrinth(self) -> NoReturn:
        logging.warning("WIP: not implemented yet, will stop unexpectedly")
        self.start_up()
        self.__start_arcane_labyrinth()
        while True:
            self.__wip()

    def __select_a_crest(self) -> None:
        _, x, y = self.wait_for_any_template(
            [
                "arcane_labyrinth/epic.png",
                "arcane_labyrinth/elite.png",
                "arcane_labyrinth/rare.png",
            ]
        )

        self.click(x, y)
        sleep(1)
        confirm = self.find_template_match("arcane_labyrinth/confirm.png")
        if confirm:
            self.click(*confirm)
        return

    def __wip(self) -> None:
        template, x, y = self.wait_for_any_template(
            [
                "arcane_labyrinth/swords_button.png",
                "arcane_labyrinth/shop_button.png",
                "arcane_labyrinth/select_a_crest.png",
            ]
        )

        if template != "arcane_labyrinth/swords_button.png":
            swords = self.find_template_match("arcane_labyrinth/swords_button.png")
            if swords:
                template = "arcane_labyrinth/swords_button.png"
                x, y = swords

        match template:
            case "arcane_labyrinth/shop_button.png":
                self.click(x, y)
                x, y = self.wait_for_template("arcane_labyrinth/onwards.png")
                while True:
                    stop = True
                    price = self.find_template_match("arcane_labyrinth/50_crystals.png")
                    if price:
                        stop = False
                        self.click(*price)
                    purchase = self.find_template_match("arcane_labyrinth/purchase.png")
                    if purchase:
                        stop = False
                        self.click(*purchase)
                    sleep(1)
                    select_a_crest = self.find_template_match(
                        "arcane_labyrinth/select_a_crest.png"
                    )
                    if select_a_crest:
                        stop = False
                        self.__select_a_crest()
                    if stop:
                        break
                self.click(x, y)
            case "arcane_labyrinth/swords_button.png":
                self.click(x, y)
                battle = self.wait_for_template("arcane_labyrinth/battle.png")
                self.click(*battle)

                try:
                    battle = self.wait_for_template(
                        "arcane_labyrinth/battle.png",
                        timeout=self.MIN_TIMEOUT,
                    )
                    self.click(*battle)
                except TimeoutException:
                    pass

                tap_to_close = self.wait_for_template(
                    "arcane_labyrinth/tap_to_close.png",
                    timeout=self.BATTLE_TIMEOUT,
                )
                self.click(*tap_to_close)
            case "arcane_labyrinth/select_a_crest.png":
                self.__select_a_crest()
        return

    def __start_arcane_labyrinth(self) -> None:
        if self.find_template_match("arcane_labyrinth/heroes_icon.png"):
            logging.info("Arcane Labyrinth already started")
            return

        self._navigate_to_default_state()
        logging.info("Navigating to Arcane Labyrinth screen")
        self.click(460, 1830, scale=True)
        self.wait_for_template(
            "duras_trials/label.png", timeout_message="Battle Modes screen not found"
        )
        self.swipe_down()
        label = self.wait_for_template("arcane_labyrinth/label.png")
        self.click(*label)
        template, x, y = self.wait_for_any_template(
            [
                "arcane_labyrinth/enter.png",
                "arcane_labyrinth/heroes_icon.png",
            ],
            timeout=self.MIN_TIMEOUT,
        )
        match template:
            case "arcane_labyrinth/enter.png":
                self.click(x, y)
                sleep(1)
                self._click_confirm_on_popup()
                self._click_confirm_on_popup()
            case "arcane_labyrinth/heroes_icon.png":
                logging.info("Arcane Labyrinth already started")
        return
