"""AFK Journey Base Module."""

import logging
import re
from abc import ABC
from collections.abc import Callable
from pathlib import Path
from time import sleep
from typing import Any

from adb_auto_player import (
    ConfigLoader,
    Coordinates,
    CropRegions,
    Game,
    MatchMode,
    NotInitializedError,
)
from adb_auto_player.games.afk_journey.config import Config


class AFKJourneyBase(Game, ABC):
    """AFK Journey Base Class."""

    def __init__(self) -> None:
        """Initialize AFKJourneyBase."""
        super().__init__()
        self.supports_portrait = True
        self.package_names = [
            "com.farlightgames.igame.gp",
        ]

    config_loader = ConfigLoader()
    games_dir: Path = config_loader.games_dir
    template_dir_path: Path | None = None
    config_file_path: Path | None = None

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

    def start_up(self, device_streaming: bool = False) -> None:
        """Give the bot eyes."""
        if self.device is None:
            logging.debug("start_up")
            self.open_eyes(device_streaming=device_streaming)
        if self.config is None:
            self.load_config()

    def get_template_dir_path(self) -> Path:
        """Retrieve path to images."""
        if self.template_dir_path is not None:
            return self.template_dir_path

        self.template_dir_path = self.games_dir / "afk_journey" / "templates"
        logging.debug(f"AFKJourney template dir: {self.template_dir_path}")
        return self.template_dir_path

    def load_config(self) -> None:
        """Load config TOML."""
        if self.config_file_path is None:
            self.config_file_path = self.games_dir / "afk_journey" / "AFKJourney.toml"
            logging.debug(f"AFK Journey config path: {self.config_file_path}")
        self.config = Config.from_toml(self.config_file_path)

    def get_config(self) -> Config:
        """Get config."""
        if self.config is None:
            raise NotInitializedError()
        return self.config

    def get_supported_resolutions(self) -> list[str]:
        """Get supported resolutions."""
        return ["1080x1920"]

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

    def _handle_battle_screen(self, use_suggested_formations: bool = True) -> bool:
        """Handles logic for battle screen.

        Args:
            use_suggested_formations: if True copy formations from Records

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
                and not self._copy_suggested_formation_from_records(formations)
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
            self.click(Coordinates(*formation_next))
            self.wait_for_roi_change(
                crop=CropRegions(left=0.2, right=0.2, top=0.15, bottom=0.8),
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

    def _copy_suggested_formation_from_records(self, formations: int = 1) -> bool:
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
            "Faramor",
            "Cyran",
            "Gerda",
            "Shemira",
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

            template, x, y = self.wait_for_any_template(
                [
                    "duras_trials/no_next.png",
                    "duras_trials/first_clear.png",
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
            elif template in ("next.png", "duras_trials/first_clear.png"):
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

    def _navigate_to_default_state(
        self, check_callable: Callable[[], bool] | None = None
    ) -> None:
        """Navigate to main default screen.

        Args:
            check_callable (Callable[[], bool] | None, optional): Callable to check.
                Defaults to None.
        """
        while True:
            if check_callable and check_callable():
                return None
            result: tuple[str, int, int] | None = self.find_any_template(
                [
                    "notice.png",
                    "confirm.png",
                    "time_of_day.png",
                    "dotdotdot.png",
                    "guide/close.png",
                    "guide/next.png",
                    "battle/copy.png",
                ]
            )

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
                    return None
                case "dotdotdot.png":
                    self.press_back_button()
                    sleep(1)
                case ("guide/close.png", "guide/next.png", "battle/copy.png"):
                    self.click(Coordinates(x=x, y=y))
                    sleep(0.5)
        return None

    def _select_afk_stage(self) -> None:
        """Selects an AFK stage template."""
        self.wait_for_template(
            template="resonating_hall.png",
            crop=CropRegions(left=0.3, right=0.3, top=0.9),
        )
        self.click(Coordinates(x=550, y=1080), scale=True)  # click rewards popup
        sleep(1)
        if self.store.get(self.STORE_SEASON, False):
            logging.debug("Clicking Talent Trials button")
            self.click(Coordinates(x=300, y=1610), scale=True)
        else:
            logging.debug("Clicking Battle button")
            self.click(Coordinates(x=800, y=1610), scale=True)
        sleep(2)
        confirm = self.game_find_template_match(
            template="confirm.png", crop=CropRegions(left=0.5, top=0.5)
        )
        if confirm:
            self.click(Coordinates(*confirm))

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
