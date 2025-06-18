"""Arcane Labyrinth Mixin."""

import logging
import time
from abc import ABC
from math import floor
from time import sleep

from adb_auto_player import (
    AutoPlayerError,
    AutoPlayerWarningError,
    Coordinates,
    CropRegions,
    GameTimeoutError,
    MatchMode,
)
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.decorators.register_custom_routine_choice import (
    register_custom_routine_choice,
)
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory


class BattleCannotBeStartedError(AutoPlayerError):
    """Battle failed to start."""

    pass


class ArcaneLabyrinthMixin(AFKJourneyBase, ABC):
    """Arcane Labyrinth Mixin."""

    arcane_skip_coordinates: tuple[int, int] | None = None
    arcane_lucky_flip_keys: int = 0
    arcane_tap_to_close_coordinates: tuple[int, int] | None = None
    arcane_difficulty_was_visible: bool = False
    arcane_difficulty_not_visible_count: int = 0

    def _add_clear_key_amount(self) -> None:
        """Clear key amount."""
        mapping: dict[int, int] = {
            1: 5,
            2: 7,
            3: 8,
            4: 8,
            5: 10,
            6: 12,
            7: 14,
            8: 16,
            9: 18,
            10: 20,
            11: 21,
            12: 22,
            13: 23,
            14: 24,
            15: 25,
        }

        keys = mapping.get(self.get_config().arcane_labyrinth.difficulty, None)
        if keys:
            self._add_keys_farmed(keys)

    def _quit(self) -> None:
        logging.info("Restarting Arcane Labyrinth")
        max_count = 30
        count = 0
        while count < max_count:
            count += 1
            result: tuple[str, int, int] | None = self.find_any_template(
                templates=[
                    "arcane_labyrinth/quit_door.png",
                    "arcane_labyrinth/exit.png",
                ],
                crop=CropRegions(left=0.7, top=0.8),
            )
            if result is None:
                self.press_back_button()
                sleep(3)
                continue
            template, x, y = result
            match template:
                case "arcane_labyrinth/quit_door.png":
                    self.tap(Coordinates(x, y))
                    sleep(0.2)
                case _:
                    self.tap(Coordinates(x, y))
                    continue
            break

        _ = self.wait_for_template(
            "arcane_labyrinth/hold_to_exit.png",
            crop=CropRegions(right=0.5, top=0.5, bottom=0.3),
            timeout_message="Failed to exit Arcane Labyrinth run",
            timeout=self.MIN_TIMEOUT,
        )
        sleep(1)
        hold_to_exit = self.wait_for_template(
            "arcane_labyrinth/hold_to_exit.png",
            crop=CropRegions(right=0.5, top=0.5, bottom=0.3),
            timeout_message="Failed to exit Arcane Labyrinth run",
            timeout=self.FAST_TIMEOUT,
        )
        self.hold(*hold_to_exit, duration=5.0)

    def _add_keys_farmed(self, keys: int) -> None:
        """Logs the number of keys farmed.

        Args:
            keys (int): Number of keys.
        """
        self.arcane_lucky_flip_keys += floor(keys * 1.2)
        logging.info(
            f"Lucky Flip Keys farmed: {self.arcane_lucky_flip_keys} "
            f"(Guild Keys: {self.arcane_lucky_flip_keys // 5}) "
        )

    @register_command(
        name="ArcaneLabyrinth",
        gui=GuiMetadata(
            label="Arcane Labyrinth",
            category=AFKJCategory.GAME_MODES,
        ),
    )
    @register_custom_routine_choice(
        label="Arcane Labyrinth",
    )
    def handle_arcane_labyrinth(self) -> None:
        """Handle Arcane Labyrinth."""
        logging.info("This is made for farming Lucky Flip Keys")
        logging.info(
            "Your current team and artifact will be used "
            "make sure to set it up once and do a single battle before"
        )
        self.start_up()
        key_quota: int = self.get_config().arcane_labyrinth.key_quota
        clear_count = 0

        while self.arcane_lucky_flip_keys < key_quota:
            try:
                self._start_arcane_labyrinth()
                while self._handle_arcane_labyrinth():
                    sleep(1)
            except AutoPlayerWarningError as e:
                logging.warning(f"{e}")
                continue
            except GameTimeoutError as e:
                logging.warning(f"{e}")
                continue
            except AutoPlayerError as e:
                logging.error(f"{e}")
                try:
                    self._quit()
                except GameTimeoutError:
                    logging.error(f"{e}")
                continue
            clear_count += 1
            logging.info(f"Arcane Labyrinth clear #{clear_count}")
            self._add_clear_key_amount()
            self.wait_for_template(
                "arcane_labyrinth/enter.png",
                crop=CropRegions(top=0.8, left=0.3),
                timeout=self.MIN_TIMEOUT,
            )
        logging.info("Arcane Labyrinth done.")
        logging.info(
            f"Key quota ({key_quota}) reached. Total: {self.arcane_lucky_flip_keys}"
        )

    def _select_a_crest(self) -> None:
        """Crest selection."""
        template, x, y = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/rarity/epic.png",
                "arcane_labyrinth/rarity/elite.png",
                "arcane_labyrinth/rarity/rare.png",
            ],
            delay=0.2,
            crop=CropRegions(right=0.8, top=0.3, bottom=0.1),
        )

        if template == "arcane_labyrinth/rarity/epic.png":
            self._add_keys_farmed(9)

        self.tap(Coordinates(x, y))
        sleep(1)
        confirm: tuple[int, int] | None = self.game_find_template_match(
            "arcane_labyrinth/confirm.png",
            crop=CropRegions(left=0.2, right=0.2, top=0.8),
        )
        if confirm:
            self.tap(Coordinates(*confirm))

    def _handle_arcane_labyrinth(self) -> bool:
        """Handle Arcane Labyrinth."""
        templates: list[str] = [
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
            delay=0.5,
        )

        match template:
            case (
                "arcane_labyrinth/blessing/set_prices.png"
                | "arcane_labyrinth/blessing/soul_blessing.png"
                | "arcane_labyrinth/blessing/epic_crest.png"
            ):
                if self.arcane_tap_to_close_coordinates is not None:
                    self.tap(Coordinates(*self.arcane_tap_to_close_coordinates))
                self.tap(Coordinates(x, y + 500))
            case (
                "arcane_labyrinth/shop_button.png"
                | "arcane_labyrinth/crest_crystal_ball.png"
            ):
                self.tap(Coordinates(x, y))
                self._handle_shop()

            case "arcane_labyrinth/swords_button.png":
                self._click_best_gate(x, y)
                self._arcane_lab_start_battle()

                start_time = time.time()
                while self._battle_is_not_completed():
                    if time.time() - start_time > self.BATTLE_TIMEOUT:
                        raise GameTimeoutError(self.BATTLE_TIMEOUT_ERROR_MESSAGE)

            case "arcane_labyrinth/select_a_crest.png" | "arcane_labyrinth/confirm.png":
                self._select_a_crest()
            case "arcane_labyrinth/quit.png":
                self.tap(Coordinates(x, y))
                return False
            case "arcane_labyrinth/tap_to_close.png":
                self.arcane_tap_to_close_coordinates = (x, y)
                self.tap(Coordinates(x, y))
                while self.game_find_template_match(
                    template="arcane_labyrinth/tap_to_close.png",
                    crop=CropRegions(top=0.8),
                ):
                    self.tap(Coordinates(x, y))
        return True

    def _arcane_lab_start_battle(self) -> None:
        """Start labyrinth battle."""
        _ = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/battle.png",
                "arcane_labyrinth/additional_challenge.png",
            ],
            threshold=0.8,
            crop=CropRegions(top=0.2, left=0.3),
        )

        sleep(1)
        battle_click_count = 0
        no_result_count = 0
        no_result_threshold = 3
        while no_result_count < no_result_threshold:
            result = self.find_any_template(
                templates=[
                    "arcane_labyrinth/battle.png",
                    "arcane_labyrinth/additional_challenge.png",
                ],
                threshold=0.8,
                crop=CropRegions(top=0.2, right=0.3),
            )
            if result is None:
                no_result_count += 1
                sleep(0.5)
                continue
            template, x, y = result
            match template:
                case "arcane_labyrinth/additional_challenge.png":
                    logging.debug(
                        "_arcane_lab_start_battle: additional challenge popup"
                    )
                    self.tap(Coordinates(x, y))
                case "arcane_labyrinth/battle.png":
                    battle_click_count += 1
                    battle_click_limit = 8
                    if battle_click_count > battle_click_limit:
                        raise BattleCannotBeStartedError("Failed to start Battle")
                    self.tap(
                        Coordinates(x, y),
                        log_message=(
                            "Tapped arcane_labyrinth/battle.png "
                            f"attempt #{battle_click_count}"
                        ),
                    )
            sleep(0.5)
        self.arcane_difficulty_was_visible = False
        sleep(1)
        self._click_confirm_on_popup()
        self._click_confirm_on_popup()

    def _handle_enter_button(self) -> None:
        """Handle entering the labyrinth."""
        difficulty: int = self.get_config().arcane_labyrinth.difficulty
        max_difficulty = 15

        if difficulty < max_difficulty and not self.game_find_template_match(
            "arcane_labyrinth/arrow_right.png"
        ):
            left_arrow: tuple[int, int] = self.wait_for_template(
                "arcane_labyrinth/arrow_left.png"
            )
            if not self.game_find_template_match("arcane_labyrinth/arrow_right.png"):
                logging.debug("Lowering difficulty")
                while (max_difficulty - difficulty) > 0:
                    self.tap(Coordinates(*left_arrow))
                    sleep(1)
                    difficulty += 1
            else:
                logging.debug("Already on lower difficulty")
        else:
            logging.debug("Already on lower difficulty")

        while enter := self.game_find_template_match(
            template="arcane_labyrinth/enter.png",
            crop=CropRegions(top=0.8, left=0.3),
        ):
            self.tap(Coordinates(*enter))
            sleep(2)

        template, _, _ = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/heroes_icon.png",
                "arcane_labyrinth/pure_crystal_icon.png",
                "arcane_labyrinth/quit_door.png",
                "arcane_labyrinth/select_a_crest.png",
                "navigation/confirm.png",
                "confirm_text.png",
            ],
            threshold=0.8,
        )

        if template in (
            "navigation/confirm.png",
            "confirm_text.png",
        ):
            checkbox = self.game_find_template_match(
                "popup/checkbox_unchecked.png",
                match_mode=MatchMode.TOP_LEFT,
                crop=CropRegions(right=0.8, top=0.2, bottom=0.6),
                threshold=0.8,
            )
            if checkbox is not None:
                self.tap(Coordinates(*checkbox))
        self._click_confirm_on_popup()
        self._click_confirm_on_popup()
        _ = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/heroes_icon.png",
                "arcane_labyrinth/pure_crystal_icon.png",
                "arcane_labyrinth/quit_door.png",
            ],
            threshold=0.7,
            timeout=self.MIN_TIMEOUT,
        )
        logging.info("Arcane Labyrinth entered")

    def _start_arcane_labyrinth(self) -> None:
        """Start Arcane Labyrinth."""
        result: tuple[int, int] | None = self.game_find_template_match(
            template="arcane_labyrinth/enter.png",
            crop=CropRegions(top=0.8, left=0.3),
        )
        if result:
            self._handle_enter_button()
            return

        if self.game_find_template_match(
            template="arcane_labyrinth/heroes_icon.png",
            threshold=0.7,
            crop=CropRegions(left=0.6, right=0.1, top=0.8),
        ):
            logging.info("Arcane Labyrinth already started")
            return

        self.navigate_to_arcane_labyrinth()

        template, x, y = self.wait_for_any_template(
            templates=[
                "arcane_labyrinth/select_a_crest.png",
                "arcane_labyrinth/confirm.png",
                "arcane_labyrinth/quit.png",
                "arcane_labyrinth/enter.png",
                "arcane_labyrinth/heroes_icon.png",
            ],
            threshold=0.7,
            timeout=self.MIN_TIMEOUT,
        )
        match template:
            case "arcane_labyrinth/enter.png":
                self._handle_enter_button()
            case "arcane_labyrinth/heroes_icon.png":
                logging.info("Arcane Labyrinth already started")
            case _:
                pass
        return

    def _battle_is_not_completed(self) -> bool:
        """Battle is not completed."""
        templates: list[str] = [
            "arcane_labyrinth/tap_to_close.png",
            "arcane_labyrinth/heroes_icon.png",
            "arcane_labyrinth/confirm.png",
            "arcane_labyrinth/quit.png",
            "navigation/confirm.png",
        ]

        if self.arcane_skip_coordinates is None:
            logging.debug("searching skip button")
            templates.insert(0, "arcane_labyrinth/skip.png")

        result: tuple[str, int, int] | None = self.find_any_template(
            templates=templates,
            threshold=0.8,
        )

        if result is None:
            if self.arcane_skip_coordinates is not None:
                self.tap(
                    Coordinates(*self.arcane_skip_coordinates),
                    log_message="Tapped skip",
                )
            difficulty: tuple[int, int] | None = self.game_find_template_match(
                template="arcane_labyrinth/difficulty.png",
                threshold=0.7,
                crop=CropRegions(bottom=0.8),
            )

            if difficulty is None and self.arcane_difficulty_was_visible:
                difficulty_check_attempts = 10
                if self.arcane_difficulty_not_visible_count > difficulty_check_attempts:
                    logging.debug("arcane_labyrinth/difficulty.png no longer visible")
                    self.arcane_difficulty_was_visible = False
                    return False
                self.arcane_difficulty_not_visible_count += 1

            if difficulty is not None:
                self.arcane_difficulty_was_visible = True
                self.arcane_difficulty_not_visible_count = 0
            sleep(0.1)

            return True

        template, x, y = result
        match template:
            case "arcane_labyrinth/tap_to_close.png":
                self.arcane_tap_to_close_coordinates = (x, y)
                self.tap(Coordinates(*self.arcane_tap_to_close_coordinates))
            case "arcane_labyrinth/skip.png":
                self.arcane_skip_coordinates = (x, y)
                self.tap(Coordinates(*self.arcane_skip_coordinates))
                return True
            case "arcane_labyrinth/battle.png":
                self._arcane_lab_start_battle()
                return True
            case "arcane_labyrinth/confirm.png":
                self._select_a_crest()
            case _:
                pass
        logging.debug(f"template: {template} found battle done")
        return False

    def _click_best_gate(self, swords_x: int, swords_y: int) -> None:
        """Click best gate."""
        logging.debug("_click_best_gate")
        sleep(0.5)
        results: list[tuple[int, int]] = self.find_all_template_matches(
            "arcane_labyrinth/swords_button.png",
            crop=CropRegions(top=0.6, bottom=0.2),
        )
        if len(results) <= 1:
            self.tap(Coordinates(swords_x, swords_y))
            return

        sleep(1)
        result: tuple[str, int, int] | None = self.find_any_template(
            templates=[
                "arcane_labyrinth/gate/relic_powerful.png",
                "arcane_labyrinth/gate/relic.png",
                "arcane_labyrinth/gate/pure_crystal.png",
                "arcane_labyrinth/gate/blessing.png",
            ],
            threshold=0.8,
            crop=CropRegions(top=0.2, bottom=0.5),
        )

        if result is None:
            logging.warning("Could not resolve best gate")
            self.tap(Coordinates(swords_x, swords_y))
            return

        template, x, y = result
        logging.debug(f"_click_best_gate: {template}")

        closest_match = min(results, key=lambda coord: abs(coord[0] - x))
        best_x, best_y = closest_match
        self.tap(Coordinates(best_x, best_y))
        return

    def _handle_shop(self) -> None:
        """Handle Fitz's Shop."""
        purchase_count = 0
        while True:
            self.wait_for_any_template(
                templates=[
                    "arcane_labyrinth/move_forward.png",
                    "arcane_labyrinth/select_a_crest.png",
                ],
                crop=CropRegions(top=0.8),
                timeout=self.MIN_TIMEOUT,
            )

            sleep(1)
            result: tuple[str, int, int] | None = self.find_any_template(
                [
                    "arcane_labyrinth/move_forward.png",
                    "arcane_labyrinth/select_a_crest.png",
                ],
                crop=CropRegions(top=0.8),
            )
            if result is None:
                break

            template, x, y = result
            purchase_limit = 2
            match template:
                case "arcane_labyrinth/move_forward.png":
                    if purchase_count >= purchase_limit:
                        break

                    # cropped in a way only the top item can be clicked
                    item_price: tuple[int, int] | None = self.game_find_template_match(
                        template="arcane_labyrinth/shop_crystal.png",
                        crop=CropRegions(left=0.7, top=0.2, bottom=0.6),
                    )
                    if item_price is None:
                        break

                    self.tap(Coordinates(*item_price))
                    sleep(0.5)
                    purchase: tuple[int, int] | None = self.game_find_template_match(
                        template="arcane_labyrinth/purchase.png",
                        crop=CropRegions(top=0.8),
                    )
                    if not purchase:
                        break
                    purchase_count += 1
                    logging.info(f"Purchase #{purchase_count}")
                    self.tap(Coordinates(*purchase))
                    sleep(0.5)
                    continue
                case "arcane_labyrinth/select_a_crest.png":
                    self._select_a_crest()

        while True:
            template, x, y = self.wait_for_any_template(
                templates=[
                    "arcane_labyrinth/move_forward.png",
                    "arcane_labyrinth/select_a_crest.png",
                ],
                crop=CropRegions(top=0.8),
                timeout=self.MIN_TIMEOUT,
            )

            match template:
                case "arcane_labyrinth/select_a_crest.png":
                    self._select_a_crest()
                case _:
                    self.tap(Coordinates(x, y))
                    break
