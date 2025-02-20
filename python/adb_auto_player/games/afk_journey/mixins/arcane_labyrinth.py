import logging
import re
from abc import ABC
from time import sleep
from typing import NoReturn

from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class DeadHeroException(Exception):
    pass


# Improvements:
# 1. Choose runes instead of blessing/item when possible
#    This would increase chance of getting epic crests which give 9 keys
# 2. Option to prioritize battles that give runes over shop/crystal ball
# 3. Choosing runes you have more of rather than at random to get better crests
# 4. Shop if you have >= 100 or >= 175 crystals
# 5. Skip items in shop only buy runes
# 6. Ignore runes we already have 8 (or 10?) copies of because you can't get crests
class ArcaneLabyrinthMixin(AFKJourneyBase, ABC):
    arcane_skip_coordinates: tuple[int, int] | None = None
    arcane_lucky_flip_keys: int = 0
    arcane_tap_to_close_coordinates: tuple[int, int] | None = None

    def __quit(self) -> None:
        logging.info("Restarting Arcane Labyrinth")
        while True:
            door = self.find_template_match("arcane_labyrinth/quit_door.png")
            if door is None:
                self.press_back_button()
                sleep(3)
                continue
            self.click(*door)
            break
        hold_to_exit = self.wait_for_template("arcane_labyrinth/hold_to_exit.png")
        self.hold(*hold_to_exit, duration=5.0)

        while True:
            result = self.find_any_template(
                templates=[
                    "arcane_labyrinth/enter.png",
                    "arcane_labyrinth/heroes_icon.png",
                ]
            )
            if result is None:
                self.click(*door)
                sleep(0.2)
            else:
                return

    def handle_arcane_labyrinth(self) -> NoReturn:
        logging.warning("This is made for farming Lucky Flip Keys")
        logging.warning(
            "It's barely functional, " "do not be surprised if it crashes randomly"
        )
        logging.warning(
            "Your current team and artifact will be used "
            "Make sure to set it up once and do a single battle before"
        )
        self.start_up()
        clear_count = 0
        while True:
            self.__start_arcane_labyrinth()
            try:
                while self.__handle_arcane_labyrinth():
                    pass
            except DeadHeroException as e:
                logging.warning(f"{e}")
                self.__quit()
                continue
            clear_count += 1
            logging.info(f"Arcane Labyrinth clear #{clear_count}")
            self.arcane_lucky_flip_keys += 25
            logging.info(f"Lucky Pick Keys farmed: {self.arcane_lucky_flip_keys}")
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
            self.arcane_lucky_flip_keys += 9
            logging.info(f"Lucky Pick Keys farmed: {self.arcane_lucky_flip_keys}")

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
                if self.arcane_tap_to_close_coordinates is not None:
                    self.click(*self.arcane_tap_to_close_coordinates)
                self.click(x, y + 500)
            case (
                "arcane_labyrinth/shop_button.png"
                | "arcane_labyrinth/crest_crystal_ball.png"
            ):
                # We are skipping this completely it is a waste of time to buy
                # Edit: I think for weaker accounts it would be more beneficial to buy
                # So should be a config option
                self.click(x, y)
                x, y = self.wait_for_template("arcane_labyrinth/onwards.png")
                self.click(x, y)
            case "arcane_labyrinth/swords_button.png":
                self.click(x, y)
                battle = self.wait_for_template("arcane_labyrinth/battle.png")
                self.click(*battle)

                while self.__battle_is_not_completed():
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
            "duras_trials/label.png",
            timeout_message="Battle Modes screen not found",
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

    def __battle_is_not_completed(self) -> bool:
        """
        :raises DeadHeroException:
        """
        dead_hero = self.find_any_template(
            templates=[
                "arcane_labyrinth/dead/celestial.png",
                "arcane_labyrinth/dead/graveborn.png",
                "arcane_labyrinth/dead/hypogean.png",
                "arcane_labyrinth/dead/lightbearer.png",
                "arcane_labyrinth/dead/mauler.png",
                "arcane_labyrinth/dead/wilder.png",
            ],
        )

        if dead_hero:
            filename, _, _ = dead_hero
            filename = re.sub(r".*/(.*?)\.png", r"\1", filename)
            faction = filename.capitalize()

            raise DeadHeroException(f"{faction} died :(")

        if self.arcane_skip_coordinates is None:
            result = self.find_any_template(
                templates=[
                    "arcane_labyrinth/tap_to_close.png",
                    "arcane_labyrinth/skip.png",
                    "arcane_labyrinth/battle.png",
                    "arcane_labyrinth/quit.png",
                    "confirm.png",
                ],
                use_previous_screenshot=True,
            )

            if not result:
                sleep(0.1)
                return True

            template, x, y = result
            match template:
                case "arcane_labyrinth/tap_to_close.png":
                    self.arcane_tap_to_close_coordinates = (x, y)
                    self.click(*self.arcane_tap_to_close_coordinates)
                    return False
                case "arcane_labyrinth/skip.png":
                    self.arcane_skip_coordinates = (x, y)
                    self.click(*self.arcane_skip_coordinates)
                case "arcane_labyrinth/battle.png":
                    self.click(x, y)
                case "arcane_labyrinth/quit.png":
                    return False
            return True

        result = self.find_any_template(
            templates=[
                "arcane_labyrinth/tap_to_close.png",
                "arcane_labyrinth/heroes_icon.png",
                "arcane_labyrinth/confirm.png",
                "arcane_labyrinth/battle.png",
                "arcane_labyrinth/quit.png",
                "confirm.png",
            ],
            use_previous_screenshot=True,
        )

        if result is None:
            self.click(*self.arcane_skip_coordinates)
            sleep(0.1)
            return True
        template, x, y = result
        match template:
            case "arcane_labyrinth/battle.png":
                self.click(x, y)
                return True
            case "arcane_labyrinth/tap_to_close.png":
                self.click(x, y)
            case "arcane_labyrinth/confirm.png":
                self.__select_a_crest()
            case _:
                pass
        return False
