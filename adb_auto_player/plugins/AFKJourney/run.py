from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any
import logging
import adb_auto_player.config_constraint as constraints
from adb_auto_player.exceptions import TimeoutException
from adb_auto_player.plugin import Plugin
from adb_auto_player.plugin_loader import get_plugins_dir


class AFKJourney(Plugin):
    BATTLE_TIMEOUT: int = 180
    STORE_SEASON: str = "SEASON"
    STORE_MODE: str = "MODE"
    MODE_DURAS_TRIALS: str = "DURAS_TRIALS"
    MODE_AFK_STAGES: str = "AFK_STAGES"
    STORE_MAX_ATTEMPTS_REACHED: str = "MAX_ATTEMPTS_REACHED"
    STORE_FORMATION_NUM: str = "FORMATION_NUM"
    CONFIG_GENERAL: str = "general"
    CONFIG_AFK_STAGES: str = "afk_stages"
    CONFIG_DURAS_TRIALS: str = "duras_trials"

    EXCLUDED_HEROES_CHOICES: list[str] = [
        "Alsa",
        "Antandra",
        "Arden",
        "Atalanta",
        "Berial",
        "Brutus",
        "Bryon",
        "Carolina",
        "Cassadee",
        "Cecia",
        "Damian",
        "Dionel",
        "Dunlingr",
        "Eironn",
        "Fae",
        "Florabelle",
        "Granny Dahnie",
        "Harak",
        "Hewynn",
        "Hodgkin",
        "Hugin",
        "Igor",
        "Kafra",
        "Koko",
        "Korin",
        "Kruger",
        "Lenya",
        "Lily May",
        "Lucca",
        "Lucius",
        "Ludovic",
        "Lumont",
        "Lyca",
        "Marilee",
        "Mikola",
        "Mirael",
        "Nara",
        "Niru",
        "Odie",
        "Phraesto",
        "Reinier",
        "Rhys",
        "Rowan",
        "Salazer",
        "Satrana",
        "Scarlita",
        "Seth",
        "Shakir",
        "Silvina",
        "Sinbad",
        "Smokey",
        "Sonja",
        "Soren",
        "Talene",
        "Tasi",
        "Temesia",
        "Thoran",
        "Ulmus",
        "Vala",
        "Valen",
        "Viperian",
        "Walker",
    ]

    def get_template_dir_path(self) -> Path:
        return get_plugins_dir() / "AFKJourney" / "templates"

    def get_menu_options(self) -> list[dict[str, Any]]:
        return [
            {
                "label": "Push Season Talent Stages",
                "action": self.push_afk_stages,
                "kwargs": {"season": True},
            },
            {
                "label": "Push AFK Stages",
                "action": self.push_afk_stages,
                "kwargs": {"season": False},
            },
            {
                "label": "Push Duras Trials",
                "action": self.push_duras_trials,
                "kwargs": {},
            },
            {
                "label": "Battle (suggested Formations)",
                "action": self.handle_battle_screen,
                "kwargs": {"use_suggested_formations": True},
            },
            {
                "label": "Battle (current Formation)",
                "action": self.handle_battle_screen,
                "kwargs": {"use_suggested_formations": False},
            },
            {
                "label": "Assist Synergy & CC",
                "action": self.assist_synergy_corrupt_creature,
                "kwargs": {},
            },
            # I already finished this, so I can't test to implement it.
            # {
            #    "label": "Season Legend Trial",
            #    "action": self.push_season_legend_trials,
            #    "kwargs": {},
            # },
        ]

    def get_config_constraints(self) -> dict[str, constraints.ConfigConstraintType]:
        return {
            "general": {
                "excluded_heroes": constraints.create_multi_checkbox_constraint(
                    choices=self.EXCLUDED_HEROES_CHOICES
                ),
                "assist_limit": constraints.create_number_constraint(),
            },
            "afk_stages": {
                "attempts": constraints.create_number_constraint(),
                "formations": constraints.create_number_constraint(maximum=7),
                "use_suggested_formations": constraints.create_checkbox_constraint(),
                "push_both_modes": constraints.create_checkbox_constraint(),
                "spend_gold": constraints.create_checkbox_constraint(),
            },
            "duras_trials": {
                "attempts": constraints.create_number_constraint(),
                "formations": constraints.create_number_constraint(maximum=7),
                "use_suggested_formations": constraints.create_checkbox_constraint(),
                "spend_gold": constraints.create_checkbox_constraint(),
            },
        }

    @dataclass
    class GeneralConfig:
        excluded_heroes: list[str]
        assist_limit: int

    def __get_general_config(self) -> GeneralConfig:
        config = self.config.get(self.CONFIG_GENERAL, {})
        return self.GeneralConfig(
            excluded_heroes=config.get("excluded_heroes", []),
            assist_limit=max(1, int(config.get("attempts", 20))),
        )

    @dataclass
    class AFKStageConfig:
        attempts: int
        formations: int
        use_suggested_formations: bool
        push_both_modes: bool
        spend_gold: bool

    def __get_afk_stage_config(self) -> AFKStageConfig:
        config = self.config.get(self.CONFIG_AFK_STAGES, {})
        return AFKJourney.AFKStageConfig(
            attempts=max(1, int(config.get("attempts", 5))),
            formations=max(1, int(config.get("formations", 7))),
            use_suggested_formations=bool(config.get("use_suggested_formations", True)),
            push_both_modes=bool(config.get("push_both_modes", True)),
            spend_gold=bool(config.get("spend_gold", True)),
        )

    @dataclass
    class DurasTrialsConfig:
        attempts: int
        formations: int
        use_suggested_formations: bool
        spend_gold: bool

    def __get_duras_trials_config(self) -> DurasTrialsConfig:
        config = self.config.get(self.CONFIG_DURAS_TRIALS, {})
        return self.DurasTrialsConfig(
            attempts=max(1, int(config.get("attempts", 5))),
            formations=max(1, int(config.get("formations", 7))),
            use_suggested_formations=bool(config.get("use_suggested_formations", True)),
            spend_gold=bool(config.get("spend_gold", True)),
        )

    def handle_battle_screen(self, use_suggested_formations: bool = True) -> bool:
        """
        Handles logic for battle screen
        :param use_suggested_formations: if False use suggested formations from records
        :return: bool
        """
        if self.store.get(self.STORE_MODE, None) == self.MODE_DURAS_TRIALS:
            formations = self.__get_duras_trials_config().formations
        else:
            formations = self.__get_afk_stage_config().formations
        self.store[self.STORE_FORMATION_NUM] = 0
        if not use_suggested_formations:
            logging.info("Not using suggested Formations")
            formations = 1

        while self.store.get(self.STORE_FORMATION_NUM, 0) < formations:
            self.store[self.STORE_FORMATION_NUM] += 1
            self.wait_for_template("records.png")

            is_multi_stage: bool = True
            if self.find_first_template_center("formation_swap.png") is None:
                is_multi_stage = False

            if (
                use_suggested_formations
                and not self.__copy_suggested_formation_from_records(formations)
            ):
                continue

            if is_multi_stage and self.__handle_multi_stage():
                return True

            if not is_multi_stage and self.__handle_single_stage():
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

            cancel = self.find_first_template_center("cancel.png")
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
            f"heroes/{name.lower().replace(" ", "")}.png": name
            for name in self.__get_general_config().excluded_heroes
        }

        if not excluded_heroes_dict:
            return None

        return self.__find_any_excluded_hero(excluded_heroes_dict)

    def __find_any_excluded_hero(self, excluded_heroes: dict[str, str]) -> str | None:
        result = self.find_any_template_center(list(excluded_heroes.keys()))
        if result is None:
            second_formation_button = self.find_first_template_center(
                "second_formation.png"
            )
            if second_formation_button:
                self.device.click(*second_formation_button)
                result = self.find_any_template_center(list(excluded_heroes.keys()))
        if result is None:
            return None

        template, _, _ = result
        return excluded_heroes.get(template)

    def __handle_multi_stage(self) -> bool:
        logging.debug("__handle_multi_stage")
        if self.store.get(self.STORE_MODE, None) == self.MODE_DURAS_TRIALS:
            attempts = self.__get_duras_trials_config().attempts
        else:
            attempts = self.__get_afk_stage_config().attempts
        count: int = 0
        count_stage_2: int = 0

        while True:
            self.wait_for_template(
                "records.png",
                timeout=self.BATTLE_TIMEOUT,
            )

            is_stage_2: bool = False
            result = self.find_first_template_center("multi_stage_first_victory.png")
            if result is None:
                count += 1
                logging.info(f"Starting Battle #{count} vs Team 1")
            else:
                count_stage_2 += 1
                logging.info(f"Starting Battle #{count_stage_2} vs Team 2")
                is_stage_2 = True

            if not self.__start_battle():
                return False

            if not is_stage_2:
                continue_button = self.wait_for_template(
                    "continue.png",
                    timeout=self.BATTLE_TIMEOUT,
                )
                self.device.click(*continue_button)
                self.wait_for_template("records.png")
                if (
                    self.find_first_template_center("multi_stage_first_victory.png")
                    is None
                ):
                    logging.info(f"Lost Battle #{count} vs Team 1")
                    if count >= attempts:
                        return False
                continue

            template, x, y = self.wait_for_any_template(
                ["result.png", "continue.png", "confirm.png"],
                timeout=self.BATTLE_TIMEOUT,
            )

            match template:
                case "confirm.png":
                    logging.warning("Battle data differs between client and server")
                    self.device.click(*template)
                    sleep(3)
                    self.__select_afk_stage()
                    return False
                case "result.png":
                    self.device.click(950, 1800)
                    return True
                case "continue.png":
                    logging.info(f"Lost Battle #{count_stage_2} vs Team 2")
                    self.device.click(x, y)
                    if count_stage_2 >= attempts:
                        self.__return_to_afk_select_to_clear_first_win_formation()
                        self.__select_afk_stage()
                        return False

    def __start_battle(self) -> bool:
        if self.store.get(self.STORE_MODE, None) == self.MODE_DURAS_TRIALS:
            spend_gold = self.__get_duras_trials_config().spend_gold
        else:
            spend_gold = self.__get_afk_stage_config().spend_gold

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

    def __return_to_afk_select_to_clear_first_win_formation(self) -> None:
        self.wait_for_template("records.png")
        sleep(1)
        logging.info("Returning to AFK Stages select")
        self.press_back_button()
        confirm = self.wait_for_template("confirm.png")
        self.device.click(*confirm)

    def __handle_single_stage(self) -> bool:
        logging.debug("__handle_single_stage")
        if self.store.get(self.STORE_MODE, None) == self.MODE_DURAS_TRIALS:
            attempts = self.__get_duras_trials_config().attempts
        else:
            attempts = self.__get_afk_stage_config().attempts
        count: int = 0
        while count < attempts:
            count += 1

            logging.info(f"Starting Battle #{count}")
            if not self.__start_battle():
                return False

            template, x, y = self.wait_for_any_template(
                [
                    "next.png",
                    "first_clear.png",
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
                case "next.png" | "first_clear.png":
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
        self.store[self.STORE_SEASON] = season
        self.store[self.STORE_MODE] = self.MODE_AFK_STAGES

        try:
            self.__start_afk_stage()
        except TimeoutException as e:
            logging.warning(f"{e}")
        if self.__get_afk_stage_config().push_both_modes:
            self.store[self.STORE_SEASON] = not season
            self.__start_afk_stage()

        return None

    def __start_afk_stage(self) -> None:
        stages_pushed: int = 0
        stages_name = self.__get_current_afk_stages_name()

        logging.info(f"Pushing: {stages_name}")
        self.__navigate_to_afk_stages_screen()
        while self.handle_battle_screen(
            self.__get_afk_stage_config().use_suggested_formations
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

    def __navigate_to_default_state(self) -> None:
        while True:
            notice = self.find_first_template_center("notice.png")
            if notice is not None:
                self.device.click(530, 1630)
                sleep(3)
                continue
            if self.find_first_template_center("time_of_day.png") is None:
                self.press_back_button()
                sleep(3)
            elif self.find_first_template_center("dotdotdot.png") is not None:
                self.press_back_button()
                sleep(1)
            else:
                break

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
        self.store[self.STORE_MODE] = self.MODE_DURAS_TRIALS
        self.__navigate_to_duras_trials_screen()

        self.wait_for_template("rate_up.png", grayscale=True)
        rate_up_banners = self.find_all_template_centers("rate_up.png", grayscale=True)

        if rate_up_banners is None:
            logging.warning(
                "Dura's Trials Rate Up banners could not be found, Stopping"
            )
            return None

        for banner in rate_up_banners:
            if self.find_first_template_center("rate_up.png", grayscale=True) is None:
                self.__navigate_to_duras_trials_screen()
                self.wait_for_template("rate_up.png", grayscale=True)

            current_banners = self.find_all_template_centers(
                "rate_up.png", grayscale=True
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
        notice = self.find_first_template_center("notice.png")
        if notice is not None:
            self.device.click(530, 1630)
            sleep(3)

        while True:
            result = self.find_any_template_center(
                ["time_of_day.png", "rate_up.png"], grayscale=True
            )
            if result is not None:
                template, _, _ = result
                break
            self.press_back_button()
            sleep(3)

        match template:
            case "time_of_day.png":
                logging.info("Clicking Battle Modes button")
                self.device.click(460, 1830)
                duras_trials_label = self.wait_for_template(
                    "duras_trials.png", timeout_message="Could not find Dura's Trials"
                )
                self.device.click(*duras_trials_label)
            case "rate_up.png":
                pass
        return None

    def __handle_dura_screen(self, x: int, y: int) -> None:
        # y+100 clicks closer to center of the button instead of rate up text
        self.device.click(x, y + 100)

        count: int = 0
        while True:
            self.wait_for_any_template(["records.png", "battle.png", "sweep.png"])
            template, x, y = self.wait_for_any_template(
                ["records.png", "battle.png", "sweep.png"]
            )
            match template:
                case "sweep.png":
                    logging.info("Dura's Trial already cleared")
                    return None
                case "battle.png":
                    self.device.click(x, y)
                case "records.png":
                    pass

            result = self.handle_battle_screen(
                self.__get_duras_trials_config().use_suggested_formations
            )

            if result is True:
                self.wait_for_template("first_clear.png")
                next_button = self.find_first_template_center("next.png")
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

    def assist_synergy_corrupt_creature(self) -> None:
        assist_limit = self.__get_general_config().assist_limit
        logging.info("Assisting Synergy and Corrupt Creature in world chat")
        count: int = 0
        while count < assist_limit:
            if self.__find_synergy_or_corrupt_creature():
                count += 1

        logging.info("Done assisting")
        return None

    def __close_profile(self) -> None:
        while self.find_first_template_center("my_formation.png"):
            self.press_back_button()
            sleep(1)
        return None

    def __find_synergy_or_corrupt_creature(self) -> bool:
        world_chat = self.find_first_template_center("world_chat.png")
        if world_chat is None:
            if self.find_first_template_center("my_formation.png"):
                self.__close_profile()
                return False
            if self.find_any_template_center(["tap_to_enter.png", "team-up_chat.png"]):
                logging.info("Switching to world chat")
                self.device.click(110, 350)
                return False
            logging.info("Opening chat")
            self.__navigate_to_default_state()
            self.device.click(1010, 1080)
            sleep(1)
            self.device.click(110, 350)
            return False
        self.device.click(260, 1400)
        try:
            self.wait_for_template("chat_button.png", delay=0.1, timeout=1)
        except TimeoutException:
            return False
        result = self.find_any_template_center(["join_now.png", "synergy.png"])
        if result is None:
            if self.find_first_template_center("world_chat.png") is None:
                if self.find_first_template_center("my_formation.png"):
                    self.__close_profile()
                else:
                    self.press_back_button()
                    sleep(1)
            return False
        template, x, y = result
        self.device.click(x, y)
        match template:
            case "join_now.png":
                logging.info("Battling Corrupt Creature")
                try:
                    return self.__handle_corrupt_creature()
                except TimeoutException:
                    logging.warning(
                        "Something went wrong when trying to battle Corrupt Creature"
                    )
                    return False
            case "synergy.png":
                logging.info("Synergy")
                return self.__handle_synergy()
        return False

    def __handle_corrupt_creature(self) -> bool:
        ready = self.wait_for_template("ready.png", timeout=10)

        self.device.click(*ready)
        # Sometimes people wait forever for a third to join...
        while self.find_first_template_center("assist_rewards_heart.png"):
            sleep(1)
        self.wait_for_template("bell.png")
        # click first 5 heroes in row 1 and 2
        for x in [110, 290, 470, 630, 800]:
            self.device.click(x, 1300)
            sleep(0.5)
        while True:
            cc_ready = self.find_first_template_center("cc_ready.png")
            if cc_ready:
                self.device.click(*cc_ready)
                sleep(1)
            else:
                break
        self.wait_for_template("assist_reward.png")
        logging.info("Corrupt Creature done")
        self.press_back_button()
        return True

    def __handle_synergy(self) -> bool:
        go = self.find_first_template_center("go.png")
        if go is None:
            return False
        self.device.click(*go)
        sleep(3)
        self.device.click(130, 900)
        sleep(1)
        self.device.click(630, 1800)

        return True
