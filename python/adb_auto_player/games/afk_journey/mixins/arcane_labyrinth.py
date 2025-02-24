import logging
from abc import ABC
from time import sleep
from typing import NoReturn

from adb_auto_player.exceptions import TimeoutException
from adb_auto_player.games.afk_journey.afk_journey_base import AFKJourneyBase


class ArcaneLabyrinthMixin(AFKJourneyBase, ABC):
    arcane_skip_coordinates: tuple[int, int] | None = None
    arcane_lucky_flip_keys: int = 0
    arcane_tap_to_close_coordinates: tuple[int, int] | None = None
    arcane_difficulty_was_visible: bool = False

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

    def _add_keys_farmed(self, keys: int):
        self.arcane_lucky_flip_keys += keys
        logging.info(
            f"Lucky Flip Keys farmed: {self.arcane_lucky_flip_keys} "
            f"(Guild Keys: {self.arcane_lucky_flip_keys // 5})"
        )

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
                while self.__handle_arcane_labyrinth():
                    sleep(1)

            except TimeoutException as e:
                logging.warning(f"{e}")
                continue
            clear_count += 1
            logging.info(f"Arcane Labyrinth clear #{clear_count}")
            self._add_keys_farmed(23)
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
            self._add_keys_farmed(9)

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
            "arcane_labyrinth/confirm.png",
            "arcane_labyrinth/tap_to_close.png",
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

            case "arcane_labyrinth/select_a_crest.png" | "arcane_labyrinth/confirm.png":
                self.__select_a_crest()
            case "arcane_labyrinth/quit.png":
                self.click(x, y)
                return False
            case "arcane_labyrinth/tap_to_close.png":
                self.arcane_tap_to_close_coordinates = (x, y)
                self.click(x, y)
                while self.find_template_match(
                    template="arcane_labyrinth/tap_to_close.png",
                    crop_top=0.8,
                ):
                    self.click(x, y)
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

        battle = self.wait_for_template(
            template="arcane_labyrinth/battle.png",
            crop_top=0.8,
            crop_left=0.3,
        )
        self.click(*battle)
        self.arcane_difficulty_was_visible = False
        sleep(2)

    def __handle_enter_button(self, x: int, y: int) -> None:
        if not self.find_template_match("arcane_labyrinth/arrow_right.png"):
            left_arrow = self.wait_for_template("arcane_labyrinth/arrow_left.png")
            if not self.find_template_match("arcane_labyrinth/arrow_right.png"):
                logging.debug("Lowering difficulty")
                self.click(*left_arrow)
                sleep(1)
                self.click(*left_arrow)
            else:
                logging.debug("Already on lower difficulty")
        else:
            logging.debug("Already on lower difficulty")

        self.click(x, y)
        while self.find_template_match(
            template="arcane_labyrinth/enter.png",
            crop_top=0.8,
            crop_left=0.3,
        ):
            self.click(x, y)
            sleep(0.5)

        template, _, _ = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/heroes_icon.png",
                "arcane_labyrinth/pure_crystal_icon.png",
                "arcane_labyrinth/quit_door.png",
                "arcane_labyrinth/select_a_crest.png",
                "confirm.png",
                "confirm_text.png",
            ],
            threshold=0.7,
        )

        if template in (
            "confirm.png",
            "confirm_text.png",
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

        def check_for_select_a_crest() -> bool:
            match = self.find_any_template(
                templates=[
                    "arcane_labyrinth/select_a_crest.png",
                    "arcane_labyrinth/confirm.png",
                ],
                crop_top=0.8,
            )

            if match is not None:
                logging.info("Select a Crest screen open")
                return True
            return False

        self._navigate_to_default_state(check_callable=check_for_select_a_crest)

        if self.find_any_template(
            templates=[
                "arcane_labyrinth/select_a_crest.png",
                "arcane_labyrinth/confirm.png",
            ],
            crop_top=0.8,
        ):
            return

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
            logging.debug("searching skip button")
            templates.insert(0, "arcane_labyrinth/skip.png")

        result = self.find_any_template(
            templates=templates,
            threshold=0.8,
        )

        if result is None:
            if self.arcane_skip_coordinates is not None:
                self.click(*self.arcane_skip_coordinates)
                logging.debug("Clicking skip")
            difficulty = self.find_template_match(
                template="arcane_labyrinth/difficulty.png",
                threshold=0.7,
                crop_bottom=0.8,
            )

            if difficulty is None and self.arcane_difficulty_was_visible:
                logging.debug("arcane_labyrinth/difficulty.png no longer visible")
                self.arcane_difficulty_was_visible = False
                return False

            if difficulty is not None:
                self.arcane_difficulty_was_visible = True
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
                "arcane_labyrinth/gate/pure_crystal.png",
                "arcane_labyrinth/gate/blessing.png",
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
                    "arcane_labyrinth/onwards.png",
                    "arcane_labyrinth/select_a_crest.png",
                ],
                crop_top=0.8,
            )
            if result is None:
                break

            template, x, y = result
            match template:
                case "arcane_labyrinth/onwards.png":
                    if purchase_count >= 2:
                        break

                    # cropped in a way only the top item can be clicked
                    item_price = self.find_template_match(
                        template="arcane_labyrinth/shop_crystal.png",
                        crop_left=0.7,
                        crop_top=0.2,
                        crop_bottom=0.6,
                    )
                    if item_price is None:
                        break

                    self.click(*item_price)
                    sleep(0.5)
                    purchase = self.find_template_match(
                        template="arcane_labyrinth/purchase.png",
                        crop_top=0.8,
                    )
                    if not purchase:
                        break
                    purchase_count += 1
                    logging.info(f"Purchase #{purchase_count}")
                    self.click(*purchase)
                    sleep(0.5)
                    continue
                case "arcane_labyrinth/select_a_crest.png":
                    self.__select_a_crest()

        while True:
            template, x, y = self.wait_for_any_template(
                templates=[
                    "arcane_labyrinth/onwards.png",
                    "arcane_labyrinth/select_a_crest.png",
                ],
                crop_top=0.8,
                timeout=self.MIN_TIMEOUT,
            )

            match template:
                case "arcane_labyrinth/select_a_crest.png":
                    self.__select_a_crest()
                case _:
                    self.click(x, y)
                    break
        return
