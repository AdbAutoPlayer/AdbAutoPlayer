import logging
import re
from abc import ABC
from time import sleep
from typing import NoReturn

from adb_auto_player.exceptions import TimeoutException
from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class DeadHeroException(Exception):
    pass


class ArcaneLabyrinthMixin(AFKJourneyBase, ABC):
    arcane_skip_coordinates: tuple[int, int] | None = None
    arcane_lucky_flip_keys: int = 0
    arcane_tap_to_close_coordinates: tuple[int, int] | None = None

    def __quit(self) -> None:
        logging.info("Restarting Arcane Labyrinth")
        x, y = 0, 0  # PyCharm complains for no reason...
        while True:
            result = self.find_any_template(
                templates=[
                    "arcane_labyrinth/quit_door.png",
                    "arcane_labyrinth/exit.png",
                ],
                crop_left=0.7,
                crop_top=0.8,
            )
            if result is None:
                self.press_back_button()
                sleep(3)
                continue
            template, x, y = result
            match template:
                case "arcane_labyrinth/quit_door.png":
                    self.click(x, y)
                    sleep(0.2)
                case _:
                    self.click(x, y)
                    continue
            break
        hold_to_exit = self.wait_for_template(
            "arcane_labyrinth/hold_to_exit.png",
            crop_right=0.5,
            crop_top=0.5,
            crop_bottom=0.3,
        )
        self.hold(*hold_to_exit, duration=5.0)

        while True:
            result = self.find_any_template(
                templates=[
                    "arcane_labyrinth/enter.png",
                    "arcane_labyrinth/heroes_icon.png",
                ],
                threshold=0.7,
                crop_top=0.8,
                crop_left=0.3,
            )
            if result is None:
                self.click(x, y)
                sleep(0.2)
            else:
                break
        return

    def handle_arcane_labyrinth(self) -> NoReturn:
        logging.warning("This is made for farming Lucky Flip Keys")
        logging.warning(
            "Your current team and artifact will be used "
            "make sure to set it up once and do a single battle before"
        )
        logging.warning("Report issues: https://discord.gg/yaphalla")
        logging.warning(
            "Channel: "
            "https://discord.com/channels/1332082220013322240/1338732933057347655"
        )
        self.start_up(device_streaming=True)
        clear_count = 0
        while True:
            try:
                self.__start_arcane_labyrinth()
                try:
                    while self.__handle_arcane_labyrinth():
                        pass
                except DeadHeroException as e:
                    logging.warning(f"{e}")
                    self.__quit()
                    continue
            except TimeoutException as e:
                logging.warning(f"{e}")
                self.__quit()
                continue
            clear_count += 1
            logging.info(f"Arcane Labyrinth clear #{clear_count}")
            self.arcane_lucky_flip_keys += 25
            logging.info(f"Lucky Flip Keys farmed: {self.arcane_lucky_flip_keys}")
            self.wait_for_template(
                "arcane_labyrinth/enter.png",
                crop_top=0.8,
                crop_left=0.3,
                timeout=self.MIN_TIMEOUT,
            )

    def __select_a_crest(self) -> None:
        template, x, y = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/rarity/epic.png",
                "arcane_labyrinth/rarity/elite.png",
                "arcane_labyrinth/rarity/rare.png",
            ],
            delay=0.2,
            crop_right=0.8,
            crop_top=0.3,
            crop_bottom=0.1,
        )

        if template == "arcane_labyrinth/rarity/epic.png":
            self.arcane_lucky_flip_keys += 9
            logging.info(f"Lucky Flip Keys farmed: {self.arcane_lucky_flip_keys}")

        self.click(x, y)
        sleep(1)
        confirm = self.find_template_match(
            "arcane_labyrinth/confirm.png",
            crop_left=0.2,
            crop_right=0.2,
            crop_top=0.8,
        )
        if confirm:
            self.click(*confirm)
        return

    def __handle_arcane_labyrinth(self) -> bool:
        templates = [
            "arcane_labyrinth/swords_button.png",
            "arcane_labyrinth/shop_button.png",
            "arcane_labyrinth/crest_crystal_ball.png",
            "arcane_labyrinth/select_a_crest.png",
            "arcane_labyrinth/quit.png",
            "arcane_labyrinth/blessing/set_prices.png",
            "arcane_labyrinth/blessing/soul_blessing.png",
            "arcane_labyrinth/blessing/epic_crest.png",
        ]
        template, x, y = self.wait_for_any_template(
            templates=templates,
            delay=0.2,
        )

        match template:
            case (
                "arcane_labyrinth/swords_button.png"
                | "arcane_labyrinth/shop_button.png"
                | "arcane_labyrinth/crest_crystal_ball.png"
            ):
                # Sleep and wait for animations to finish
                sleep(0.5)
                template, x, y = self.wait_for_any_template(
                    templates=templates,
                    delay=0.2,
                )
            case _:
                pass

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
                self.click(x, y)
                self.__handle_shop()

            case "arcane_labyrinth/swords_button.png":
                self.__click_best_gate(x, y)
                self.__arcane_lab_start_battle()
                while self.__battle_is_not_completed():
                    pass

            case "arcane_labyrinth/select_a_crest.png":
                self.__select_a_crest()
            case "arcane_labyrinth/quit.png":
                self.click(x, y)
                return False
        return True

    def __arcane_lab_start_battle(self):
        template, x, y = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/battle.png",
                "arcane_labyrinth/additional_challenge.png",
            ],
            threshold=0.8,
        )

        match template:
            case "arcane_labyrinth/additional_challenge.png":
                logging.debug("__arcane_lab_start_battle: additional challenge popup")
                self.click(x, y)
            case _:
                pass
        sleep(0.5)

        while True:
            template, x, y = self.wait_for_any_template(
                templates=[
                    "arcane_labyrinth/battle.png",
                    "arcane_labyrinth/additional_challenge.png",
                ],
                threshold=0.8,
                crop_top=0.2,
                crop_left=0.3,
            )
            match template:
                case "arcane_labyrinth/additional_challenge.png":
                    logging.debug(
                        "__arcane_lab_start_battle: additional challenge popup"
                    )
                    self.click(x, y)
                case _:
                    break

        self.__check_for_dead_hero()
        battle = self.wait_for_template(
            template="arcane_labyrinth/battle.png",
            crop_top=0.8,
            crop_left=0.3,
        )
        self.click(*battle)

    def __handle_enter_button(self, x: int, y: int) -> None:
        self.click(x, y)

        template, _, _ = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/heroes_icon.png",
                "arcane_labyrinth/pure_crystal_icon.png",
                "arcane_labyrinth/quit_door.png",
                "confirm.png",
                "confirm_text.png",
            ],
            threshold=0.7,
        )

        if template not in (
            "arcane_labyrinth/heroes_icon.png",
            "arcane_labyrinth/pure_crystal_icon.png",
            "arcane_labyrinth/quit_door.png",
        ):
            checkbox = self.find_template_match("battle/checkbox_unchecked.png")
            if checkbox is not None:
                self.click(*checkbox)
        self._click_confirm_on_popup()
        self._click_confirm_on_popup()
        self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/heroes_icon.png",
                "arcane_labyrinth/pure_crystal_icon.png",
                "arcane_labyrinth/quit_door.png",
            ],
            threshold=0.7,
            timeout=self.MIN_TIMEOUT,
        )
        logging.info("Arcane Labyrinth entered")

    def __start_arcane_labyrinth(self) -> None:
        result = self.find_template_match(
            template="arcane_labyrinth/enter.png",
            crop_top=0.8,
            crop_left=0.3,
        )
        if result:
            self.__handle_enter_button(*result)
            return

        if self.find_template_match(
            template="arcane_labyrinth/heroes_icon.png",
            threshold=0.7,
            crop_left=0.6,
            crop_right=0.1,
            crop_top=0.8,
        ):
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
            timeout=self.MIN_TIMEOUT,
        )
        self.swipe_down()
        label = self.wait_for_template(
            "arcane_labyrinth/label.png",
            timeout=self.MIN_TIMEOUT,
        )
        self.click(*label)
        template, x, y = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/enter.png",
                "arcane_labyrinth/heroes_icon.png",
            ],
            threshold=0.7,
            crop_top=0.8,
            crop_left=0.3,
            timeout=self.MIN_TIMEOUT,
        )
        match template:
            case "arcane_labyrinth/enter.png":
                self.__handle_enter_button(x, y)
            case "arcane_labyrinth/heroes_icon.png":
                logging.info("Arcane Labyrinth already started")
        return

    def __battle_is_not_completed(self) -> bool:
        logging.debug("__battle_is_not_completed")

        templates = [
            "arcane_labyrinth/tap_to_close.png",
            "arcane_labyrinth/heroes_icon.png",
            "arcane_labyrinth/confirm.png",
            "arcane_labyrinth/quit.png",
            "confirm.png",
        ]

        if self.arcane_skip_coordinates is None:
            templates.insert(0, "arcane_labyrinth/skip.png")

        result = self.find_any_template(
            templates=templates,
            threshold=0.8,
        )

        if result is None:
            if self.arcane_skip_coordinates is not None:
                self.click(*self.arcane_skip_coordinates)
            sleep(0.1)
            return True

        template, x, y = result
        match template:
            case "arcane_labyrinth/tap_to_close.png":
                self.arcane_tap_to_close_coordinates = (x, y)
                self.click(*self.arcane_tap_to_close_coordinates)
            case "arcane_labyrinth/skip.png":
                self.arcane_skip_coordinates = (x, y)
                self.click(*self.arcane_skip_coordinates)
                return True
            case "arcane_labyrinth/battle.png":
                while self.find_template_match(
                    template="arcane_labyrinth/battle.png",
                    crop_top=0.8,
                    crop_left=0.3,
                ):
                    self.click(x, y)
                return True
            case "arcane_labyrinth/confirm.png":
                self.__select_a_crest()
            case _:
                pass
        return False

    def __click_best_gate(self, swords_x: int, swords_y: int) -> None:
        logging.debug("__click_best_gate")
        sleep(0.5)
        results = self.find_all_template_matches(
            "arcane_labyrinth/swords_button.png",
            crop_top=0.6,
            crop_bottom=0.2,
            use_previous_screenshot=True,
        )
        if len(results) <= 1:
            self.click(swords_x, swords_y)
            return

        sleep(1)
        result = self.find_any_template(
            templates=[
                "arcane_labyrinth/gate/relic_powerful.png",
                "arcane_labyrinth/gate/relic.png",
                "arcane_labyrinth/gate/blessing.png",
                "arcane_labyrinth/gate/pure_crystal.png",
            ],
            threshold=0.8,
            crop_top=0.2,
            crop_bottom=0.5,
            use_previous_screenshot=True,
        )

        if result is None:
            logging.warning("Could not resolve best gate")
            self.click(swords_x, swords_y)
            return

        template, x, y = result
        logging.debug(f"__click_best_gate: {template}")

        closest_match = min(results, key=lambda coord: abs(coord[0] - x))
        best_x, best_y = closest_match
        self.click(best_x, best_y)
        return

    def __check_for_dead_hero(self) -> None:
        logging.debug("__check_for_dead_hero")
        dead_hero = self.find_any_template(
            templates=[
                "arcane_labyrinth/dead/celestial.png",
                "arcane_labyrinth/dead/graveborn.png",
                "arcane_labyrinth/dead/hypogean.png",
                "arcane_labyrinth/dead/lightbearer.png",
                "arcane_labyrinth/dead/mauler.png",
                "arcane_labyrinth/dead/wilder.png",
            ],
            threshold=0.98,
            crop_top=0.6,
            crop_bottom=0.1,
        )

        if dead_hero:
            filename, _, _ = dead_hero
            filename = re.sub(r".*/(.*?)\.png", r"\1", filename)
            faction = filename.capitalize()
            raise DeadHeroException(f"{faction} died :(")
        return

    def __handle_shop(self) -> None:
        purchase_count = 0
        while True:
            self.wait_for_any_template(
                templates=[
                    "arcane_labyrinth/onwards.png",
                    "arcane_labyrinth/select_a_crest.png",
                ],
                crop_top=0.8,
                timeout=self.MIN_TIMEOUT,
            )

            sleep(1)
            result = self.find_any_template(
                [
                    "arcane_labyrinth/50_crystals.png",
                    "arcane_labyrinth/select_a_crest.png",
                ],
                crop_left=0.2,
                crop_top=0.1,
            )
            if result is None:
                break

            template, x, y = result
            match template:
                case "arcane_labyrinth/50_crystals.png":
                    if purchase_count >= 2:
                        break
                    self.click(x, y)
                    sleep(0.5)
                    purchase = self.find_template_match(
                        template="arcane_labyrinth/purchase.png",
                        crop_top=0.8,
                    )
                    if not purchase:
                        break
                    purchase_count += 1
                    self.click(*purchase)
                    continue
                case "arcane_labyrinth/select_a_crest.png":
                    self.__select_a_crest()

        x, y = self.wait_for_template(
            "arcane_labyrinth/onwards.png",
            crop_top=0.8,
            crop_right=0.6,
            timeout=self.MIN_TIMEOUT,
        )
        self.click(x, y)
        return
