"""AFK Journey Base Module."""

import logging
import re
from abc import ABC
from collections.abc import Callable
from time import sleep
from typing import Any

from adb_auto_player import (
    Coordinates,
    CropRegions,
    Game,
    MatchMode,
)
from adb_auto_player.games.afk_journey.config import Config


class AFKJourneyBase(Game, ABC):
    """AFK Journey Base Class."""

    def __init__(self) -> None:
        """Initialize AFKJourneyBase."""
        super().__init__()
        self.supports_portrait = True
        self.package_name_substrings = [
            "com.farlightgames.igame.gp",
        ]

        # to allow passing properties over multiple functions
        self.store: dict[str, Any] = {}

    # Timeout constants (in seconds)
    BATTLE_TIMEOUT: int = 180
    MIN_TIMEOUT: int = 10
    FAST_TIMEOUT: int = 3

    # Store keys
    STORE_SEASON: str = "SEASON"
    STORE_MODE: str = "MODE"
    STORE_MAX_ATTEMPTS_REACHED: str = "MAX_ATTEMPTS_REACHED"
    STORE_FORMATION_NUM: str = "FORMATION_NUM"

    # Game modes
    MODE_DURAS_TRIALS: str = "DURAS_TRIALS"
    MODE_AFK_STAGES: str = "AFK_STAGES"
    MODE_LEGEND_TRIALS: str = "LEGEND_TRIALS"

    # Language Requirements
    LANG_ERROR: str = "Is the game language set to English?"

    def start_up(self, device_streaming: bool = False) -> None:
        """Give the bot eyes."""
        if self.device is None:
            logging.debug("start_up")
            self.open_eyes(device_streaming=device_streaming)

    def _load_config(self) -> Config:
        """Load config TOML."""
        self.config = Config.from_toml(self._get_config_file_path())
        return self.config

    def get_config(self) -> Config:
        """Get config."""
        if self.config is None:
            return self._load_config()
        return self.config

    def _get_config_attribute_from_mode(self, attribute: str) -> Any:
        """Retrieve a configuration attribute based on the current game mode.

        Args:
            attribute (str): The name of the configuration attribute to retrieve.

        Returns:
            The value of the specified attribute from the configuration corresponding
            to the current game mode.
        """
        match self.store.get(self.STORE_MODE, None):
            case self.MODE_DURAS_TRIALS:
                return getattr(self.get_config().duras_trials, attribute)
            case self.MODE_LEGEND_TRIALS:
                return getattr(self.get_config().legend_trials, attribute)
            case _:
                return getattr(self.get_config().afk_stages, attribute)

    def _handle_battle_screen(
        self, use_suggested_formations: bool = True, skip_manual: bool = False
    ) -> bool:
        """Handles logic for battle screen.

        Args:
            use_suggested_formations: if True copy formations from Records
            skip_manual: Skip formations labeled as manual clear.

        Returns:
            True if the battle was won, False otherwise.
        """
        self.start_up()

        formations = self._get_config_attribute_from_mode("formations")

        self.store[self.STORE_FORMATION_NUM] = 0
        if not use_suggested_formations:
            formations = 1

        while self.store.get(self.STORE_FORMATION_NUM, 0) < formations:
            self.store[self.STORE_FORMATION_NUM] += 1

            if (
                use_suggested_formations
                and not self._copy_suggested_formation_from_records(
                    formations, skip_manual
                )
            ):
                continue
            else:
                self.wait_for_any_template(
                    templates=[
                        "battle/records.png",
                        "battle/formations_icon.png",
                    ],
                    crop=CropRegions(top=0.5),
                )

            if self._handle_single_stage():
                return True

            if self.store.get(self.STORE_MAX_ATTEMPTS_REACHED, False):
                self.store[self.STORE_MAX_ATTEMPTS_REACHED] = False
                return False

        if formations > 1:
            logging.info("Stopping Battle, tried all attempts for all Formations")
        return False

    def _copy_suggested_formation(
        self, formations: int = 1, start_count: int = 1
    ) -> bool:
        """Helper to copy suggested formations from records.

        Args:
            formations (int): Number of formation to copy
            start_count (int): First formation to copy

        Returns:
            True if successful, False otherwise
        """
        formation_num = self.store.get(self.STORE_FORMATION_NUM, 0)

        if formations < formation_num:
            return False

        logging.info(f"Copying Formation #{formation_num}")
        counter = formation_num - start_count
        while counter > 0:
            formation_next: tuple[int, int] = self.wait_for_template(
                "battle/formation_next.png",
                crop=CropRegions(left=0.8, top=0.5, bottom=0.4),
                timeout=self.MIN_TIMEOUT,
                timeout_message=f"Formation #{formation_num} not found",
            )
            start_image = self.get_screenshot()
            self.click(Coordinates(*formation_next))
            self.wait_for_roi_change(
                start_image=start_image,
                crop=CropRegions(left=0.2, right=0.2, top=0.15, bottom=0.8),
                threshold=0.8,
                timeout=self.MIN_TIMEOUT,
            )
            counter -= 1
        excluded_hero: str | None = self._formation_contains_excluded_hero()
        if excluded_hero is not None:
            logging.warning(
                f"Formation contains excluded Hero: '{excluded_hero}' skipping"
            )
            start_count = self.store[self.STORE_FORMATION_NUM]
            self.store[self.STORE_FORMATION_NUM] += 1
            return self._copy_suggested_formation(formations, start_count)
        return True

    def _copy_suggested_formation_from_records(
        self, formations: int = 1, skip_manual: bool = False
    ) -> bool:
        """Copy suggested formations from records.

        Returns:
            True if successful, False otherwise.
        """
        records: tuple[int, int] = self.wait_for_template(
            template="battle/records.png",
            crop=CropRegions(right=0.5, top=0.8),
        )
        self.click(Coordinates(*records))
        copy: tuple[int, int] = self.wait_for_template(
            "battle/copy.png",
            crop=CropRegions(left=0.3, right=0.1, top=0.7, bottom=0.1),
            timeout=self.MIN_TIMEOUT,
            timeout_message="No formations available for this battle",
        )
        start_count = 1

        while True:
            if not self._copy_suggested_formation(formations, start_count):
                return False
            if skip_manual:
                sleep(2)
                manual_clear: tuple[int, int] | None = self.game_find_template_match(
                    "battle/manual_battle.png",
                    crop=CropRegions(top=0.5),
                )
                if manual_clear:
                    logging.info("Manual formation found, skipping.")
                    start_count = self.store.get(self.STORE_FORMATION_NUM, 1)
                    self.store[self.STORE_FORMATION_NUM] += 1
                    continue

            self.click(Coordinates(*copy))
            sleep(1)

            cancel = self.game_find_template_match(
                template="cancel.png",
                crop=CropRegions(left=0.1, right=0.5, top=0.6, bottom=0.3),
            )
            if cancel:
                logging.warning(
                    "Formation contains locked Artifacts or Heroes skipping"
                )
                self.click(Coordinates(*cancel))
                start_count = self.store.get(self.STORE_FORMATION_NUM, 1)
                self.store[self.STORE_FORMATION_NUM] += 1
            else:
                self._click_confirm_on_popup()
                logging.debug("Formation copied")
                return True

    def _formation_contains_excluded_hero(self) -> str | None:
        """Skip formations with excluded heroes.

        Returns:
            str | None: Name of excluded hero
        """
        excluded_heroes_dict: dict[str, str] = {
            f"heroes/{re.sub(r'[\s&]', '', name.value.lower())}.png": name.value
            for name in self.get_config().general.excluded_heroes
        }

        if not excluded_heroes_dict:
            return None

        excluded_heroes_missing_icon: set[str] = {
            "Nothing as of now :)",
        }
        filtered_dict = {}

        for key, value in excluded_heroes_dict.items():
            if value in excluded_heroes_missing_icon:
                logging.warning(f"Missing icon for Hero: {value}")
            else:
                filtered_dict[key] = value

        return self._find_any_excluded_hero(filtered_dict)

    def _find_any_excluded_hero(self, excluded_heroes: dict[str, str]) -> str | None:
        """Find excluded hero templates.

        Args:
            excluded_heroes (dict[str, str]): Dictionary of excluded heroes.

        Returns:
            str | None: Name of excluded hero
        """
        result: tuple[str, int, int] | None = self.find_any_template(
            templates=list(excluded_heroes.keys()),
            crop=CropRegions(left=0.1, right=0.2, top=0.3, bottom=0.4),
        )
        if result is None:
            return None

        template, _, _ = result
        return excluded_heroes.get(template)

    def _start_battle(self) -> bool:
        """Begin battle.

        Returns:
            bool: True if battle started, False otherwise.
        """
        spend_gold: str = self._get_config_attribute_from_mode("spend_gold")

        result: tuple[str, int, int] = self.wait_for_any_template(
            templates=[
                "battle/records.png",
                "battle/formations_icon.png",
            ],
            crop=CropRegions(top=0.5),
        )

        if result is None:
            return False
        self.click(Coordinates(x=850, y=1780), scale=True)
        template, x, y = result
        self.wait_until_template_disappears(template, crop=CropRegions(top=0.5))
        sleep(1)

        # Need to double-check the order of prompts here
        if self.find_any_template(["battle/spend.png", "battle/gold.png"]):
            if spend_gold:
                logging.warning("Not spending gold returning")
                self.store[self.STORE_MAX_ATTEMPTS_REACHED] = True
                self.press_back_button()
                return False
            else:
                self._click_confirm_on_popup()

        while self.find_any_template(
            [
                "battle/no_hero_is_placed_on_the_talent_buff_tile.png",
                "duras_trials/blessed_heroes_specific_tiles.png",
            ],
        ):
            checkbox = self.game_find_template_match(
                "battle/checkbox_unchecked.png",
                match_mode=MatchMode.TOP_LEFT,
                crop=CropRegions(right=0.8, top=0.2, bottom=0.6),
                threshold=0.8,
            )
            if checkbox is None:
                logging.error('Could not find "Don\'t remind for x days" checkbox')
            else:
                self.click(Coordinates(*checkbox))
            self._click_confirm_on_popup()

        self._click_confirm_on_popup()
        return True

    def _click_confirm_on_popup(self) -> bool:
        """Confirm popups.

        Returns:
            bool: True if confirmed, False if not.
        """
        result: tuple[str, int, int] | None = self.find_any_template(
            templates=["confirm.png", "confirm_text.png"], crop=CropRegions(top=0.4)
        )
        if result:
            _, x, y = result
            self.click(Coordinates(x=x, y=y))
            sleep(1)
            return True
        return False

    def _handle_single_stage(self) -> bool:
        """Handles a single stage of a battle.

        Returns:
            bool: True if the battle was successful, False if not.
        """
        logging.debug("_handle_single_stage")
        attempts = self._get_config_attribute_from_mode("attempts")
        count = 0
        result: bool | None = None

        while count < attempts:
            count += 1
            logging.info(f"Starting Battle #{count}")

            if not self._start_battle():
                result = False
                break

            # TODO: would have to be refactored completely to check if
            #       a battle is still going on afk stages and season talent stages
            #       have a label at the top, not sure about other game modes
            #       would also have to check every couple seconds if the frame
            #       changed to see if the game froze.

            # TODO: Because we iteratively look for templates, it can match something
            # later in the list first causing non-deterministic behavior.
            _, x, y = self.wait_for_any_template(
                [
                    "duras_trials/no_next.png",
                    "duras_trials/first_clear.png",
                    "duras_trials/end_sunrise.png",
                    "next.png",
                    "battle/victory_rewards.png",
                    "retry.png",
                    "confirm.png",
                    "battle/victory_rewards.png",  # TODO: Duplicate? Check if needed.
                    "battle/power_up.png",
                    "battle/result.png",
                ],
                timeout=self.BATTLE_TIMEOUT,
            )
            # TODO: Temporary fix of restarting search once battle end is determined.
            template, x, y = self.wait_for_any_template(
                [
                    "duras_trials/no_next.png",
                    "duras_trials/first_clear.png",
                    "duras_trials/end_sunrise.png",
                    "next.png",
                    "battle/victory_rewards.png",
                    "retry.png",
                    "confirm.png",
                    "battle/victory_rewards.png",  # TODO: Duplicate? Check if needed.
                    "battle/power_up.png",
                    "battle/result.png",
                ],
                timeout=self.BATTLE_TIMEOUT,
            )

            if template == "duras_trials/no_next.png":
                self.press_back_button()
                result = True
                break
            elif template == "battle/victory_rewards.png":
                self.click(Coordinates(x=550, y=1800), scale=True)
                result = True
                break
            elif template == "battle/power_up.png":
                self.click(Coordinates(x=550, y=1800), scale=True)
                result = False
                break
            elif template == "confirm.png":
                logging.error(
                    "Network Error or Battle data differs between client and server"
                )
                self.click(Coordinates(x=x, y=y))
                sleep(3)
                result = False
                break
            elif template in (
                "next.png",
                "duras_trials/first_clear.png",
                "duras_trials/end_sunrise.png",
            ):
                result = True
                break
            elif template == "retry.png":
                logging.info(f"Lost Battle #{count}")
                self.click(Coordinates(x=x, y=y))
                # Do not break so the loop continues
            elif template == "battle/result.png":
                self.click(Coordinates(x=950, y=1800), scale=True)
                result = True
                break

        # If no branch set result, default to False.
        if result is None:
            result = False

        return result

    def _navigate_to_default_state(  # noqa: PLR0912
        self, check_callable: Callable[[], bool] | None = None
    ) -> None:
        """Navigate to main default screen.

        Args:
            check_callable (Callable[[], bool] | None, optional): Callable to check.
                Defaults to None.
        """
        templates = [
            "notice.png",
            "confirm.png",
            "time_of_day.png",
            "dotdotdot.png",
            "battle/copy.png",
            "guide/close.png",
            "guide/next.png",
            "battle/copy.png",
            "login/claim.png",
        ]

        while True:
            if not self.is_game_running():
                logging.warning("Trying to restart app this is still WIP.")
                self.start_game()
                sleep(15)
                while not self.find_any_template(templates) and self.is_game_running():
                    self.tap(Coordinates(1080 // 2, 1920 // 2))
                    sleep(3)

            if check_callable and check_callable():
                sleep(1)
                return None
            result: tuple[str, int, int] | None = self.find_any_template(templates)

            if result is None:
                logging.debug("back")
                self.press_back_button()
                sleep(3)
                continue

            template, x, y = result
            logging.debug(template)
            match template:
                case "notice.png":
                    self.click(Coordinates(x=530, y=1630), scale=True)
                    sleep(3)
                    continue
                case "exit.png":
                    pass
                case "confirm.png":
                    if self.game_find_template_match(
                        "exit_the_game.png",
                    ):
                        x_btn: tuple[int, int] | None = self.game_find_template_match(
                            "x.png",
                        )
                        if x_btn:
                            logging.debug("x")
                            self.click(Coordinates(*x_btn))
                            sleep(1)
                            continue
                        self.press_back_button()
                        sleep(1)
                    else:
                        self.click(Coordinates(x=x, y=y))
                        sleep(1)
                case "time_of_day.png":
                    break
                case "dotdotdot.png":
                    self.press_back_button()
                    sleep(1)
                case _:
                    self.click(Coordinates(x=x, y=y))
                    sleep(0.5)
        sleep(1)
        return

    def _handle_guide_popup(
        self,
    ) -> None:
        """Close out of guide popups."""
        while True:
            result: tuple[str, int, int] | None = self.find_any_template(
                templates=["guide/close.png", "guide/next.png"],
                crop=CropRegions(top=0.4),
            )
            if result is None:
                break
            _, x, y = result
            self.click(Coordinates(x=x, y=y))
            sleep(1)
