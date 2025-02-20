import logging
from abc import ABC
from time import sleep
from typing import NoReturn

from adb_auto_player.exceptions import TimeoutException
from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class ArcaneLabyrinthMixin(AFKJourneyBase, ABC):
    skip_coordinates: tuple[int, int] | None = None
    lucky_flip_keys: int = 0

    def handle_arcane_labyrinth(self) -> NoReturn:
        logging.warning("This is made for farming Lucky Flip Keys")
        logging.warning(
            "It's barely functional, " "do not be surprised if it crashes randomly"
        )
        logging.warning(
            "Your current team and artifact will be used"
            "Make sure to set it up once and do a single battle before"
        )
        self.start_up()
        clear_count = 0
        while True:
            self.__start_arcane_labyrinth()
            while self.__handle_arcane_labyrinth():
                pass
            clear_count += 1
            logging.info(f"Arcane Labyrinth clear #{clear_count}")
            self.lucky_flip_keys += 25
            logging.info(f"Lucky Pick Keys farmed: {self.lucky_flip_keys}")
            self.wait_for_template("arcane_labyrinth/enter.png")

    def __select_a_crest(self) -> None:
        template, x, y = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/rarity/epic.png",
                "arcane_labyrinth/rarity/elite.png",
                "arcane_labyrinth/rarity/rare.png",
            ],
            delay=0.2,
        )

        if template == "arcane_labyrinth/rarity/epic.png":
            self.lucky_flip_keys += 9
            logging.info(f"Lucky Pick Keys farmed: {self.lucky_flip_keys}")

        self.click(x, y)
        sleep(1)
        confirm = self.find_template_match("arcane_labyrinth/confirm.png")
        if confirm:
            self.click(*confirm)
        return

    def __handle_arcane_labyrinth(self) -> bool:
        template, x, y = self.wait_for_any_template(
            templates=[
                # Shop and Crystal Ball have higher prio for fast clears
                "arcane_labyrinth/shop_button.png",
                "arcane_labyrinth/crest_crystal_ball.png",
                # There should be a config for weaker accounts to prefer battles
                # So they actually survive till floor 15 and clear it
                "arcane_labyrinth/swords_button.png",
                "arcane_labyrinth/select_a_crest.png",
                "arcane_labyrinth/quit.png",
                "arcane_labyrinth/blessing/set_prices.png",
                "arcane_labyrinth/blessing/soul_blessing.png",
                "arcane_labyrinth/blessing/epic_crest.png",
            ],
            delay=0.2,
        )

        match template:
            case (
                "arcane_labyrinth/blessing/set_prices.png"
                | "arcane_labyrinth/blessing/soul_blessing.png"
                | "arcane_labyrinth/blessing/epic_crest.png"
            ):
                self.click(x, y + 200)
            case "arcane_labyrinth/shop_button.png":
                # We are skipping the shop completely it is a waste of time to buy
                # Edit: I think for weaker accounts it would be more beneficial to buy
                # So should be a config option
                self.click(x, y)
                x, y = self.wait_for_template("arcane_labyrinth/onwards.png")
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
                while self.__try_to_skip_battle():
                    pass

            case "arcane_labyrinth/select_a_crest.png":
                self.__select_a_crest()
            case "arcane_labyrinth/quit.png":
                self.click(x, y)
                return False
        return True

    def __start_arcane_labyrinth(self) -> None:
        result = self.find_template_match("arcane_labyrinth/enter.png")
        if result:
            self.click(*result)
            self.wait_for_template("arcane_labyrinth/heroes_icon.png")
            logging.info("Arcane Labyrinth entered")
            return

        if self.find_template_match("arcane_labyrinth/heroes_icon.png"):
            logging.info("Arcane Labyrinth already started")
            return

        logging.info("Navigating to Arcane Labyrinth screen")
        # Possibility of getting stuck
        # Back button does not work on Arcane Labyrinth screen
        self._navigate_to_default_state()
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

    def __try_to_skip_battle(self) -> bool:
        if self.skip_coordinates is None:
            result = self.find_any_template(
                [
                    "arcane_labyrinth/tap_to_close.png",
                    "arcane_labyrinth/skip.png",
                ]
            )

            if not result:
                sleep(0.25)
                return True

            template, x, y = result
            match template:
                case "arcane_labyrinth/tap_to_close.png":
                    self.click(x, y)
                    return False
                case "arcane_labyrinth/skip.png":
                    self.skip_coordinates = (x, y)
                    self.click(x, y)
            return True

        tap = self.find_template_match("arcane_labyrinth/tap_to_close.png")
        if not tap:
            self.click(*self.skip_coordinates)
            sleep(0.25)
            return True
        self.click(*tap)
        return False
