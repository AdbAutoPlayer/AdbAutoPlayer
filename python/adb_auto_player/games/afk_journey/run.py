import re
from pathlib import Path
from time import sleep
import logging
from typing import Callable

from adb_auto_player.command import Command
from adb_auto_player.exceptions import TimeoutException, NotFoundException
from adb_auto_player.games.afk_journey.config import Config
from adb_auto_player.games.game import Game
from adb_auto_player.config_loader import get_games_dir
from adb_auto_player.screen_utils import MatchMode


class AFKJourney(Game):
    BATTLE_TIMEOUT: int = 180
    STORE_SEASON: str = "SEASON"
    STORE_MODE: str = "MODE"
    MODE_DURAS_TRIALS: str = "DURAS_TRIALS"
    MODE_AFK_STAGES: str = "AFK_STAGES"
    MODE_LEGEND_TRIALS: str = "LEGEND_TRIALS"
    STORE_MAX_ATTEMPTS_REACHED: str = "MAX_ATTEMPTS_REACHED"
    STORE_FORMATION_NUM: str = "FORMATION_NUM"
    CONFIG_GENERAL: str = "general"
    CONFIG_AFK_STAGES: str = "afk_stages"
    CONFIG_DURAS_TRIALS: str = "duras_trials"

    template_dir_path: Path | None = None
    config_file_path: Path | None = None

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

    def get_supported_resolutions(self) -> list[str]:
        return ["1080x1920"]

    def get_menu_commands(self) -> list[Command]:
        return [
            Command(
                name="SeasonTalentStages",
                action=self.push_afk_stages,
                kwargs={"season": True},
            ),
            Command(
                name="AFKStages",
                action=self.push_afk_stages,
                kwargs={"season": False},
            ),
            Command(
                name="DurasTrials",
                action=self.push_duras_trials,
                kwargs={},
            ),
            Command(
                name="BattleSuggested",
                action=self.handle_battle_screen,
                kwargs={"use_suggested_formations": True},
            ),
            Command(
                name="Battle",
                action=self.handle_battle_screen,
                kwargs={"use_suggested_formations": False},
            ),
            Command(
                name="AssistSynergyAndCC",
                action=self.assist_synergy_corrupt_creature,
                kwargs={},
            ),
            Command(
                name="LegendTrials",
                action=self.push_legend_trials,
                kwargs={},
            ),
        ]

    def __get_config_attribute_from_mode(self, attribute: str):
        match self.store.get(self.STORE_MODE, None):
            case self.MODE_DURAS_TRIALS:
                return getattr(self.config.duras_trials, attribute)
            case self.MODE_LEGEND_TRIALS:
                return getattr(self.config.legend_trials, attribute)
            case _:
                return getattr(self.config.afk_stages, attribute)

    def handle_battle_screen(self, use_suggested_formations: bool = True) -> bool:
        """
        Handles logic for battle screen
        :param use_suggested_formations: if False use suggested formations from records
        :return: bool
        """
        self.start_up()

        formations = self.__get_config_attribute_from_mode("formations")

        self.store[self.STORE_FORMATION_NUM] = 0
        if not use_suggested_formations:
            logging.info("Not using suggested Formations")
            formations = 1

        while self.store.get(self.STORE_FORMATION_NUM, 0) < formations:
            self.store[self.STORE_FORMATION_NUM] += 1

            if (
                use_suggested_formations
                and not self.__copy_suggested_formation_from_records(formations)
            ):
                continue
            else:
                self.wait_for_template("records.png")

            if self.__handle_single_stage():
                return True

            if self.store.get(self.STORE_MAX_ATTEMPTS_REACHED, False):
                self.store[self.STORE_MAX_ATTEMPTS_REACHED] = False
                return False

        logging.info("Stopping Battle, tried all attempts for all Formations")
        return False

    def __copy_suggested_formation(
        self, formations: int = 1, start_count: int = 0
    ) -> bool:
        formation_num = self.store.get(self.STORE_FORMATION_NUM, 0)

        if formations < formation_num:
            return False

        logging.info(f"Copying Formation #{formation_num}")
        counter = formation_num - start_count
        while counter > 1:
            formation_next = self.wait_for_template(
                "formation_next.png",
                timeout=5,
                timeout_message=f"Formation #{formation_num} not found",
            )
            self.device.click(*formation_next)
            sleep(1)
            counter -= 1
        sleep(1)
        excluded_hero = self.__formation_contains_excluded_hero()
        if excluded_hero is not None:
            logging.warning(
                f"Formation contains excluded Hero: '{excluded_hero}' skipping"
            )
            self.store[self.STORE_FORMATION_NUM] += 1
            return self.__copy_suggested_formation(formations, start_count + 1)
        return True

    def __copy_suggested_formation_from_records(self, formations: int = 1) -> bool:
        records = self.wait_for_template("records.png")
        self.device.click(*records)
        copy = self.wait_for_template("copy.png", timeout=5)

        start_count = 0
        while True:
            if not self.__copy_suggested_formation(formations, start_count):
                return False
            self.device.click(*copy)
            sleep(1)

            cancel = self.find_template_match("cancel.png")
            if cancel:
                logging.warning(
                    "Formation contains locked Artifacts or Heroes skipping"
                )
                self.device.click(*cancel)
                start_count = self.store.get(self.STORE_FORMATION_NUM, 1) - 1
                self.store[self.STORE_FORMATION_NUM] += 1
            else:
                self.__click_confirm_on_popup()
                logging.debug("Formation copied")
                return True

    def __formation_contains_excluded_hero(self) -> str | None:
        excluded_heroes_dict = {
            f"heroes/{re.sub(r"[\s&]", "", name.lower())}.png": name
            for name in self.config.general.excluded_heroes
        }

        if not excluded_heroes_dict:
            return None

        excluded_heroes_missing_icon = {
            "Valka",
            "Callan" "Cryonaia",
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
        result = self.find_any_template_center(list(excluded_heroes.keys()))
        if result is None:
            return None

        template, _, _ = result
        return excluded_heroes.get(template)

    def __start_battle(self) -> bool:
        spend_gold = self.__get_config_attribute_from_mode("spend_gold")

        self.wait_for_template("records.png")
        self.device.click(850, 1780)
        self.wait_until_template_disappears("records.png")
        sleep(1)

        if self.find_any_template_center(["spend.png", "gold.png"]) and not spend_gold:
            logging.warning("Not spending gold returning")
            self.store[self.STORE_MAX_ATTEMPTS_REACHED] = True
            self.press_back_button()
            return False

        self.__click_confirm_on_popup()
        self.__click_confirm_on_popup()
        return True

    def __click_confirm_on_popup(self) -> bool:
        result = self.find_any_template_center(["confirm.png", "confirm_text.png"])
        if result:
            _, x, y = result
            self.device.click(x, y)
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
                    "next.png",
                    "duras_trials/first_clear.png",
                    "retry.png",
                    "confirm.png",
                    "result.png",
                ],
                timeout=self.BATTLE_TIMEOUT,
            )

            match template:
                case "confirm.png":
                    logging.warning("Battle data differs between client and server")
                    self.device.click(*template)
                    sleep(3)
                    self.__select_afk_stage()
                    return False
                case "next.png" | "duras_trials/first_clear.png":
                    return True
                case "retry.png":
                    logging.info(f"Lost Battle #{count}")
                    self.device.click(x, y)
                case "result.png":
                    self.device.click(950, 1800)
                    return True
        return False

    def push_afk_stages(self, season: bool) -> None:
        """
        Entry for pushing AFK Stages
        :param season: Push Season Stage if True otherwise push regular AFK Stages
        """
        self.start_up()
        self.store[self.STORE_SEASON] = season
        self.store[self.STORE_MODE] = self.MODE_AFK_STAGES

        try:
            self.__start_afk_stage()
        except TimeoutException as e:
            logging.warning(f"{e}")
        if self.config.afk_stages.push_both_modes:
            self.store[self.STORE_SEASON] = not season
            self.__start_afk_stage()
        return None

    def __start_afk_stage(self) -> None:
        stages_pushed: int = 0
        stages_name = self.__get_current_afk_stages_name()

        logging.info(f"Pushing: {stages_name}")
        self.__navigate_to_afk_stages_screen()
        while self.handle_battle_screen(
            self.config.afk_stages.use_suggested_formations
        ):
            stages_pushed += 1
            logging.info(f"{stages_name} pushed: {stages_pushed}")
        return None

    def __get_current_afk_stages_name(self) -> str:
        season = self.store.get(self.STORE_SEASON, False)
        if season:
            return "Season Talent Stages"
        return "AFK Stages"

    def __navigate_to_afk_stages_screen(self) -> None:
        logging.info("Navigating to default state")
        self.__navigate_to_default_state()
        logging.info("Navigating to AFK Stage Battle screen")
        self.device.click(90, 1830)
        self.__select_afk_stage()

    def __navigate_to_default_state(
        self, check_callable: Callable[[], bool] = None
    ) -> None:
        while True:
            if check_callable and check_callable():
                return None
            result = self.find_any_template_center(
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
                    self.device.click(530, 1630)
                    sleep(3)
                case "confirm.png":
                    self.device.click(x, y)
                    sleep(1)
                case "time_of_day.png":
                    return None
                case "dotdotdot.png":
                    self.press_back_button()
                    sleep(1)
        return None

    def __select_afk_stage(self) -> None:
        self.wait_for_template("resonating_hall.png")
        self.device.click(550, 1080)  # click rewards popup
        sleep(1)
        if self.store.get(self.STORE_SEASON, False):
            logging.debug("Clicking Talent Trials button")
            self.device.click(300, 1610)
        else:
            logging.debug("Clicking Battle button")
            self.device.click(800, 1610)
        return None

    def push_duras_trials(self) -> None:
        """
        Entry for pushing Dura's Trials
        :return:
        """
        self.start_up()
        logging.warning("Not updated for S3 run at your own risk")
        self.store[self.STORE_MODE] = self.MODE_DURAS_TRIALS
        self.__navigate_to_duras_trials_screen()

        self.wait_for_template("duras_trials/rate_up.png", grayscale=True)
        rate_up_banners = self.find_all_template_matches(
            "duras_trials/rate_up.png", grayscale=True, use_previous_screenshot=True
        )

        if not rate_up_banners:
            logging.warning(
                "Dura's Trials Rate Up banners could not be found, Stopping"
            )
            return None

        for banner in rate_up_banners:
            if (
                self.find_template_match("duras_trials/rate_up.png", grayscale=True)
                is None
            ):
                self.__navigate_to_duras_trials_screen()
                self.wait_for_template("duras_trials/rate_up.png", grayscale=True)

            current_banners = self.find_all_template_matches(
                "duras_trials/rate_up.png", grayscale=True, use_previous_screenshot=True
            )

            if current_banners is None:
                logging.warning(
                    "Dura's Trials Rate Up banners could not be found, Stopping"
                )
                return None

            if len(current_banners) != len(rate_up_banners):
                logging.warning("Dura's Trials schedule changed, Stopping")
                return None

            self.__handle_dura_screen(*banner)

        return None

    def __navigate_to_duras_trials_screen(self) -> None:
        logging.info("Navigating to Dura's Trial select")

        def check_for_duras_trials_label() -> bool:
            label = self.find_template_match("duras_trials/label.png")
            return label is not None

        self.__navigate_to_default_state(check_callable=check_for_duras_trials_label)

        duras_trials_label = self.find_template_match(
            "duras_trials/label.png", use_previous_screenshot=True
        )
        if duras_trials_label is None:
            logging.info("Clicking Battle Modes button")
            self.device.click(460, 1830)
            duras_trials_label = self.wait_for_template(
                "duras_trials/label.png", timeout_message="Could not find Dura's Trials"
            )
        self.device.click(*duras_trials_label)
        return None

    def __handle_dura_screen(self, x: int, y: int) -> None:
        # y+100 clicks closer to center of the button instead of rate up text
        self.device.click(x, y + 100)

        count: int = 0
        while True:
            self.wait_for_any_template(
                ["records.png", "duras_trials/battle.png", "duras_trials/sweep.png"]
            )
            template, x, y = self.wait_for_any_template(
                ["records.png", "duras_trials/battle.png", "duras_trials/sweep.png"]
            )
            match template:
                case "duras_trials/sweep.png":
                    logging.info("Dura's Trial already cleared")
                    return None
                case "duras_trials/battle.png":
                    self.device.click(x, y)
                case "records.png":
                    pass

            result = self.handle_battle_screen(
                self.config.duras_trials.use_suggested_formations
            )

            if result is True:
                self.wait_for_template("duras_trials/first_clear.png")
                next_button = self.find_template_match("next.png")
                if next_button is not None:
                    count += 1
                    logging.info(f"Trials pushed: {count}")
                    self.device.click(*next_button)
                    self.device.click(*next_button)
                    sleep(3)
                    continue
                else:
                    logging.info("Dura's Trial completed")
                    return None
            logging.info("Dura's Trial failed")
            return None
        return None

    def assist_synergy_corrupt_creature(self) -> None:
        self.start_up()
        assist_limit = self.config.general.assist_limit
        logging.info("Assisting Synergy and Corrupt Creature in world chat")
        count: int = 0
        while count < assist_limit:
            if self.__find_synergy_or_corrupt_creature():
                count += 1

        logging.info("Done assisting")
        return None

    def __find_synergy_or_corrupt_creature(self) -> bool:
        result = self.find_any_template_center(
            [
                "assist/world_chat.png",
                "assist/tap_to_enter.png",
                "assist/team-up_chat.png",
            ]
        )
        if result is None:
            logging.info("Opening chat")
            self.__navigate_to_default_state()
            self.device.click(1010, 1080)
            sleep(1)
            self.device.click(110, 350)
            return False

        template, x, y = result
        match template:
            case "assist/world_chat.png":
                self.device.click(260, 1400)
            case "assist/tap_to_enter.png", "assist/team-up_chat.png":
                logging.info("Switching to world chat")
                self.device.click(110, 350)
                return False

        try:
            template, x, y = self.wait_for_any_template(
                ["assist/join_now.png", "assist/synergy.png", "assist/chat_button.png"],
                delay=0.1,
                timeout=1,
            )
        except TimeoutException:
            return False
        if "assist/chat_button.png" == template:
            if self.find_template_match("world_chat.png") is None:
                self.press_back_button()
                sleep(1)
            return False
        self.device.click(x, y)
        match template:
            case "assist/join_now.png":
                logging.info("Battling Corrupt Creature")
                try:
                    return self.__handle_corrupt_creature()
                except TimeoutException:
                    logging.warning(
                        "Something went wrong when trying to battle Corrupt Creature"
                    )
                    return False
            case "assist/synergy.png":
                logging.info("Synergy")
                return self.__handle_synergy()
        return False

    def __handle_corrupt_creature(self) -> bool:
        ready = self.wait_for_template("assist/ready.png", timeout=10)

        self.device.click(*ready)
        # Sometimes people wait forever for a third to join...
        self.wait_until_template_disappears(
            "assist/rewards_heart.png", timeout=self.BATTLE_TIMEOUT
        )
        self.wait_for_template("assist/bell.png")
        # click first 5 heroes in row 1 and 2
        for x in [110, 290, 470, 630, 800]:
            self.device.click(x, 1300)
            sleep(0.5)
        while True:
            cc_ready = self.find_template_match("assist/cc_ready.png")
            if cc_ready:
                self.device.click(*cc_ready)
                sleep(1)
            else:
                break
        self.wait_for_template("assist/reward.png")
        logging.info("Corrupt Creature done")
        self.press_back_button()
        return True

    def __handle_synergy(self) -> bool:
        go = self.find_template_match("assist/go.png")
        if go is None:
            return False
        self.device.click(*go)
        sleep(3)
        self.device.click(130, 900)
        sleep(1)
        self.device.click(630, 1800)
        return True

    def start_up(self) -> None:
        if self.device is None:
            logging.debug("start_up")
            self.set_device()
        if self.config is None:
            self.load_config()
        return None

    def push_legend_trials(self) -> None:
        self.start_up()
        self.store[self.STORE_MODE] = self.MODE_LEGEND_TRIALS

        try:
            self.__navigate_to_legend_trials_select_tower()
        except TimeoutException as e:
            logging.error(f"{e}")
            return None
        results = self.find_all_template_matches(
            "legend_trials/go_lightborn.png", grayscale=True
        )
        # TODO check wilder and graveborn tmrw
        for result in results:
            self.__navigate_to_legend_trials_select_tower()
            self.device.click(*result)
            try:
                self.__select_legend_trials_floor()
            except TimeoutException | NotFoundException as e:
                logging.error(f"{e}")
                self.press_back_button()
                sleep(3)
                continue
            self.__handle_legend_trials_battle()
        logging.error("Not Implemented")
        return None

    def __handle_legend_trials_battle(self) -> None:
        count: int = 0
        while True:
            result = self.handle_battle_screen(
                self.config.legend_trials.use_suggested_formations
            )

            if result is True:
                next_btn = self.wait_for_template("next.png")
                if next_btn is not None:
                    count += 1
                    logging.info(f"Trials pushed: {count}")
                    self.device.click(*next_btn)
                    continue
                else:
                    logging.warning(
                        "Not implemented assuming this shows up after the last floor?"
                    )
                    return None
            logging.info("Legend Trial failed")
            return None
        return None

    def __select_legend_trials_floor(self) -> None:
        logging.debug("__select_legend_trials_floor")
        _, x, y = self.wait_for_any_template(
            [
                "legend_trials/tower_icon_lightborn.png",
                # "legend_trials/tower_icon_wilder.png",
                # "legend_trials/tower_icon_graveborn.png",
                "legend_trials/tower_icon_mauler.png",
            ]
        )
        sleep(1)
        result = self.find_template_match(
            "legend_trials/info_icon.png",
            match_mode=MatchMode.BOTTOM_RIGHT,
        )
        if result is None:
            raise NotFoundException("legend_trials/info_icon.png not found")

        x, y = result
        if x < 500:
            self.device.click(x + 200, y - 50)
        else:
            self.device.click(x - 200, y - 50)
        return None

    def __navigate_to_legend_trials_select_tower(self) -> None:
        logging.info("Navigating to Legend Trials tower selection")

        def check_for_legend_trials_s_header() -> bool:
            header = self.find_template_match("legend_trials/s_header.png")
            return header is not None

        self.__navigate_to_default_state(
            check_callable=check_for_legend_trials_s_header
        )

        s_header = self.find_template_match(
            "legend_trials/s_header.png", use_previous_screenshot=True
        )
        if not s_header:
            logging.info("Clicking Battle Modes button")
            self.device.click(460, 1830)
            label = self.wait_for_template(
                "legend_trials/label.png",
                timeout_message="Could not find Legend Trial Label",
            )
            self.device.click(*label)
            self.wait_for_template(
                "legend_trials/s_header.png",
                timeout_message="Could not find Season Legend Trial Header",
            )
        return None
