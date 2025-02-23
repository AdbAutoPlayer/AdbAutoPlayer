import logging
import re
from abc import ABC
from time import sleep
from typing import Callable

from adb_auto_player.config_loader import get_games_dir
from adb_auto_player.exceptions import NotInitializedError
from adb_auto_player.game import Game
from pathlib import Path

from adb_auto_player.games.afk_journey.config import Config
from adb_auto_player.template_matching import MatchMode


class AFKJourneyBase(Game, ABC):
    def __init__(self) -> None:
        super().__init__()
        self.supports_portrait = True

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

    def start_up(self) -> None:
        if self.device is None:
            logging.debug("start_up")
            self.set_device()
        if self.config is None:
            self.load_config()
        return None

    def get_template_dir_path(self) -> Path:
        if self.template_dir_path is not None:
            return self.template_dir_path

        games_dir = get_games_dir()
        self.template_dir_path = games_dir / "afk_journey" / "templates"
        logging.debug(f"AFKJourney template dir: {self.template_dir_path}")
        return self.template_dir_path

    def load_config(self) -> None:
        if self.config_file_path is None:
            self.config_file_path = get_games_dir() / "afk_journey" / "AFKJourney.toml"
            logging.debug(f"AFK Journey config path: {self.config_file_path}")
        self.config = Config.from_toml(self.config_file_path)

    def get_config(self) -> Config:
        if self.config is None:
            raise NotInitializedError()
        return self.config

    def get_supported_resolutions(self) -> list[str]:
        return ["1080x1920", "9:16"]

    def __get_config_attribute_from_mode(self, attribute: str):
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
        """
        self.start_up()

        formations = self.__get_config_attribute_from_mode("formations")

        self.store[self.STORE_FORMATION_NUM] = 0
        if not use_suggested_formations:
            formations = 1

        while self.store.get(self.STORE_FORMATION_NUM, 0) < formations:
            self.store[self.STORE_FORMATION_NUM] += 1

            if (
                use_suggested_formations
                and not self.__copy_suggested_formation_from_records(formations)
            ):
                continue
            else:
                self.wait_for_any_template(
                    templates=[
                        "battle/records.png",
                        "battle/formations_icon.png",
                    ],
                    crop_top=0.5,
                )

            if self.__handle_single_stage():
                return True

            if self.store.get(self.STORE_MAX_ATTEMPTS_REACHED, False):
                self.store[self.STORE_MAX_ATTEMPTS_REACHED] = False
                return False

        if formations > 1:
            logging.info("Stopping Battle, tried all attempts for all Formations")
        return False

    def __copy_suggested_formation(
        self, formations: int = 1, start_count: int = 1
    ) -> bool:
        formation_num = self.store.get(self.STORE_FORMATION_NUM, 0)

        if formations < formation_num:
            return False

        logging.info(f"Copying Formation #{formation_num}")
        counter = formation_num - start_count
        while counter > 0:
            formation_next = self.wait_for_template(
                "battle/formation_next.png",
                crop_left=0.8,
                crop_top=0.5,
                crop_bottom=0.4,
                timeout=self.MIN_TIMEOUT,
                timeout_message=f"Formation #{formation_num} not found",
            )
            self.click(*formation_next)
            self.wait_for_roi_change(
                crop_left=0.2,
                crop_right=0.2,
                crop_top=0.15,
                crop_bottom=0.8,
                timeout=self.MIN_TIMEOUT,
            )
            counter -= 1
        excluded_hero = self.__formation_contains_excluded_hero()
        if excluded_hero is not None:
            logging.warning(
                f"Formation contains excluded Hero: '{excluded_hero}' skipping"
            )
            start_count = self.store[self.STORE_FORMATION_NUM]
            self.store[self.STORE_FORMATION_NUM] += 1
            return self.__copy_suggested_formation(formations, start_count)
        return True

    def __copy_suggested_formation_from_records(self, formations: int = 1) -> bool:
        records = self.wait_for_template(
            template="battle/records.png",
            crop_right=0.5,
            crop_top=0.8,
        )
        self.click(*records)
        copy = self.wait_for_template(
            "battle/copy.png",
            crop_left=0.3,
            crop_right=0.1,
            crop_top=0.7,
            crop_bottom=0.1,
            timeout=self.MIN_TIMEOUT,
            timeout_message="No formations available for this battle",
        )

        start_count = 1
        while True:
            if not self.__copy_suggested_formation(formations, start_count):
                return False
            self.click(*copy)
            sleep(1)

            cancel = self.find_template_match("cancel.png")
            if cancel:
                logging.warning(
                    "Formation contains locked Artifacts or Heroes skipping"
                )
                self.click(*cancel)
                start_count = self.store.get(self.STORE_FORMATION_NUM, 1)
                self.store[self.STORE_FORMATION_NUM] += 1
            else:
                self._click_confirm_on_popup()
                logging.debug("Formation copied")
                return True

    def __formation_contains_excluded_hero(self) -> str | None:
        excluded_heroes_dict = {
            f"heroes/{re.sub(r'[\s&]', '', name.value.lower())}.png": name.value
            for name in self.get_config().general.excluded_heroes
        }

        if not excluded_heroes_dict:
            return None

        excluded_heroes_missing_icon = {
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

        return self.__find_any_excluded_hero(filtered_dict)

    def __find_any_excluded_hero(self, excluded_heroes: dict[str, str]) -> str | None:
        result = self.find_any_template(
            templates=list(excluded_heroes.keys()),
            crop_left=0.1,
            crop_right=0.2,
            crop_top=0.3,
            crop_bottom=0.4,
        )
        if result is None:
            return None

        template, _, _ = result
        return excluded_heroes.get(template)

    def __start_battle(self) -> bool:
        spend_gold = self.__get_config_attribute_from_mode("spend_gold")

        result = self.wait_for_any_template(
            templates=[
                "battle/records.png",
                "battle/formations_icon.png",
            ],
            crop_top=0.5,
        )

        if result is None:
            return False
        self.click(850, 1780, scale=True)
        template, x, y = result
        self.wait_until_template_disappears(
            template,
            crop_top=0.5,
        )
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
            checkbox = self.find_template_match(
                "battle/checkbox_unchecked.png",
                match_mode=MatchMode.TOP_LEFT,
                crop_right=0.8,
                crop_top=0.2,
                crop_bottom=0.6,
                use_previous_screenshot=True,
            )
            if checkbox is None:
                logging.error('Could not find "Don\'t remind for x days" checkbox')
            else:
                self.click(*checkbox)
            self._click_confirm_on_popup()

        self._click_confirm_on_popup()
        return True

    def _click_confirm_on_popup(self) -> bool:
        result = self.find_any_template(
            templates=["confirm.png", "confirm_text.png"],
            crop_top=0.4,
        )
        if result:
            _, x, y = result
            self.click(x, y)
            sleep(1)
            return True
        return False

    def __handle_single_stage(self) -> bool:
        logging.debug("__handle_single_stage")
        attempts = self.__get_config_attribute_from_mode("attempts")
        count: int = 0
        while count < attempts:
            count += 1

            logging.info(f"Starting Battle #{count}")
            if not self.__start_battle():
                return False

            template, x, y = self.wait_for_any_template(
                [
                    "duras_trials/no_next.png",
                    "duras_trials/first_clear.png",
                    "next.png",
                    "battle/victory_rewards.png",
                    "retry.png",
                    "confirm.png",
                    "battle/power_up.png",
                    "battle/result.png",
                ],
                timeout=self.BATTLE_TIMEOUT,
            )

            match template:
                case "duras_trials/no_next.png":
                    self.press_back_button()
                    return True
                case "battle/victory_rewards.png":
                    self.click(550, 1800, scale=True)
                    return True
                case "battle/power_up.png":
                    self.click(550, 1800, scale=True)
                    return False
                case "confirm.png":
                    logging.warning("Battle data differs between client and server")
                    self.click(*template)
                    sleep(3)
                    self._select_afk_stage()
                    return False
                case "next.png" | "duras_trials/first_clear.png":
                    return True
                case "retry.png":
                    logging.info(f"Lost Battle #{count}")
                    self.click(x, y)
                case "battle/result.png":
                    self.click(950, 1800, scale=True)
                    return True
        return False

    def _navigate_to_default_state(
        self, check_callable: Callable[[], bool] | None = None
    ) -> None:
        while True:
            if check_callable and check_callable():
                return None
            result = self.find_any_template(
                [
                    "notice.png",
                    "confirm.png",
                    "time_of_day.png",
                    "dotdotdot.png",
                ]
            )

            if result is None:
                self.press_back_button()
                sleep(3)
                continue

            template, x, y = result
            match template:
                case "notice.png":
                    self.click(530, 1630, scale=True)
                    sleep(3)
                case "exit.png":
                    pass
                case "confirm.png":
                    if self.find_template_match(
                        "exit_the_game.png",
                        crop_top=0.4,
                        crop_bottom=0.4,
                        use_previous_screenshot=True,
                    ):
                        x_btn = self.find_template_match(
                            "x.png",
                            crop_left=0.6,
                            crop_right=0.3,
                            crop_top=0.6,
                            crop_bottom=0.2,
                            use_previous_screenshot=True,
                        )
                        if x_btn:
                            self.click(*x_btn)
                    else:
                        self.click(x, y)
                        sleep(1)
                case "time_of_day.png":
                    return None
                case "dotdotdot.png":
                    self.press_back_button()
                    sleep(1)
        return None

    def _select_afk_stage(self) -> None:
        self.wait_for_template(
            template="resonating_hall.png",
            crop_left=0.3,
            crop_right=0.3,
            crop_top=0.9,
        )
        self.click(550, 1080, scale=True)  # click rewards popup
        sleep(1)
        if self.store.get(self.STORE_SEASON, False):
            logging.debug("Clicking Talent Trials button")
            self.click(300, 1610, scale=True)
        else:
            logging.debug("Clicking Battle button")
            self.click(800, 1610, scale=True)
        sleep(2)
        confirm = self.find_template_match(
            template="confirm.png",
            crop_left=0.5,
            crop_top=0.5,
        )
        if confirm:
            self.click(*confirm)
        return None

    def _handle_guide_popup(
        self,
        use_previous_screenshot=False,
    ) -> None:
        while True:
            result = self.find_any_template(
                templates=["guide/close.png", "guide/next.png"],
                crop_top=0.4,
                use_previous_screenshot=use_previous_screenshot,
            )
            if result is None:
                break
            _, x, y = result
            self.click(x, y)
            sleep(1)
        return
