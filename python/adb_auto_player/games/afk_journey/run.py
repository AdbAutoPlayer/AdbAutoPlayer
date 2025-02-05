import re
from pathlib import Path
from time import sleep
import logging
from typing import Callable, NoReturn

from adb_auto_player.command import Command
from adb_auto_player.exceptions import (
    TimeoutException,
    NotFoundException,
    NotInitializedError,
)
from adb_auto_player.games.afk_journey.config import Config
from adb_auto_player.games.game import Game
from adb_auto_player.config_loader import get_games_dir


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
                name="AssistSynergyAndCC",
                action=self.assist_synergy_corrupt_creature,
                kwargs={},
            ),
            Command(
                name="LegendTrials",
                action=self.push_legend_trials,
                kwargs={},
            ),
            Command(
                name="EventGuildChatClaim",
                action=self.event_guild_chat_claim,
                kwargs={},
            ),
            Command(
                name="EventMonopolyAssist",
                action=self.event_monopoly_assist,
                kwargs={},
            ),
        ]

    def __get_config_attribute_from_mode(self, attribute: str):
        match self.store.get(self.STORE_MODE, None):
            case self.MODE_DURAS_TRIALS:
                return getattr(self.get_config().duras_trials, attribute)
            case self.MODE_LEGEND_TRIALS:
                return getattr(self.get_config().legend_trials, attribute)
            case _:
                return getattr(self.get_config().afk_stages, attribute)

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
                    ["battle/records.png", "battle/formations_icon.png"]
                )

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
                "battle/formation_next.png",
                timeout=5,
                timeout_message=f"Formation #{formation_num} not found",
            )
            self.click(*formation_next)
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
        records = self.wait_for_template("battle/records.png")
        self.click(*records)
        copy = self.wait_for_template(
            "copy.png",
            timeout=5,
            timeout_message="No formations available for this battle",
        )

        start_count = 0
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
                start_count = self.store.get(self.STORE_FORMATION_NUM, 1) - 1
                self.store[self.STORE_FORMATION_NUM] += 1
            else:
                self.__click_confirm_on_popup()
                logging.debug("Formation copied")
                return True

    def __formation_contains_excluded_hero(self) -> str | None:
        excluded_heroes_dict = {
            f"heroes/{re.sub(r"[\s&]", "", name.lower())}.png": name
            for name in self.get_config().general.excluded_heroes
        }

        if not excluded_heroes_dict:
            return None

        excluded_heroes_missing_icon = {
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
        result = self.find_any_template(list(excluded_heroes.keys()))
        if result is None:
            return None

        template, _, _ = result
        return excluded_heroes.get(template)

    def __start_battle(self) -> bool:
        spend_gold = self.__get_config_attribute_from_mode("spend_gold")

        result = self.wait_for_any_template(
            ["battle/records.png", "battle/formations_icon.png"]
        )
        if result is None:
            return False
        self.click(850, 1780, scale=True)
        template, x, y = result
        match template:
            case "battle/records.png":
                self.wait_until_template_disappears("battle/records.png")
            case "battle/formations_icon.png":
                self.wait_until_template_disappears("battle/formations_icon.png")
        sleep(1)

        if self.find_any_template(["spend.png", "gold.png"]) and not spend_gold:
            logging.warning("Not spending gold returning")
            self.store[self.STORE_MAX_ATTEMPTS_REACHED] = True
            self.press_back_button()
            return False

        self.__click_confirm_on_popup()
        self.__click_confirm_on_popup()
        return True

    def __click_confirm_on_popup(self) -> bool:
        result = self.find_any_template(["confirm.png", "confirm_text.png"])
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
                delay=3,
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
                    self.__select_afk_stage()
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
        if self.get_config().afk_stages.push_both_modes:
            self.store[self.STORE_SEASON] = not season
            self.__start_afk_stage()
        return None

    def __start_afk_stage(self) -> None:
        stages_pushed: int = 0
        stages_name = self.__get_current_afk_stages_name()

        logging.info(f"Pushing: {stages_name}")
        self.__navigate_to_afk_stages_screen()
        while self.handle_battle_screen(
            self.get_config().afk_stages.use_suggested_formations
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
        self.click(90, 1830, scale=True)
        self.__select_afk_stage()

    def __navigate_to_default_state(
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
                        "exit_the_game.png", use_previous_screenshot=True
                    ):
                        x_btn = self.find_template_match(
                            "x.png", use_previous_screenshot=True
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

    def __select_afk_stage(self) -> None:
        self.wait_for_template("resonating_hall.png")
        self.click(550, 1080, scale=True)  # click rewards popup
        sleep(1)
        if self.store.get(self.STORE_SEASON, False):
            logging.debug("Clicking Talent Trials button")
            self.click(300, 1610, scale=True)
        else:
            logging.debug("Clicking Battle button")
            self.click(800, 1610, scale=True)
        sleep(2)
        confirm = self.find_template_match("confirm.png")
        if confirm:
            self.click(*confirm)
        return None

    def push_duras_trials(self) -> None:
        """
        Entry for pushing Dura's Trials
        :return:
        """
        self.start_up()
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

        first_banner = True
        for banner in rate_up_banners:
            if not first_banner:
                self.__navigate_to_duras_trials_screen()
            self.__handle_dura_screen(*banner)
            self.__navigate_to_duras_trials_screen()
            self.__handle_dura_screen(*banner, nightmare_mode=True)
            first_banner = False

        return None

    def __navigate_to_duras_trials_screen(self) -> None:
        logging.info("Navigating to Dura's Trial select")

        def check_for_duras_trials_label() -> bool:
            match = self.find_template_match("duras_trials/featured_heroes.png")
            return match is not None

        self.__navigate_to_default_state(check_callable=check_for_duras_trials_label)

        featured_heroes = self.find_template_match(
            "duras_trials/featured_heroes.png",
            use_previous_screenshot=True,
        )
        if featured_heroes is not None:
            return

        logging.info("Clicking Battle Modes button")
        self.click(460, 1830, scale=True)
        duras_trials_label = self.wait_for_template("duras_trials/label.png")
        self.click(*duras_trials_label)
        self.wait_for_template("duras_trials/featured_heroes.png")
        return None

    def __handle_dura_screen(
        self, x: int, y: int, nightmare_mode: bool = False
    ) -> None:
        # y+100 clicks closer to center of the button instead of rate up text
        offset = int(self.get_scale_factor() * 100)
        self.click(x, y + offset)

        count: int = 0
        while True:
            template, _, _ = self.wait_for_any_template(
                [
                    "battle/records.png",
                    "duras_trials/battle.png",
                    "duras_trials/sweep.png",
                ]
            )

            if nightmare_mode and template != "battle/records.png":
                nightmare = self.find_template_match("duras_trials/nightmare.png")
                if nightmare is None:
                    logging.warning("Nightmare Button not found")
                    return None
                self.click(*nightmare)
                template, x, y = self.wait_for_any_template(
                    [
                        "duras_trials/nightmare_swords.png",
                        "duras_trials/cleared.png",
                    ]
                )
                match template:
                    case "duras_trials/nightmare_swords.png":
                        self.click(x, y)
                    case "duras_trials/cleared.png":
                        logging.info("Nightmare Trial already cleared")
                        return None
            else:
                template, x, y = self.wait_for_any_template(
                    [
                        "battle/records.png",
                        "duras_trials/battle.png",
                        "duras_trials/sweep.png",
                    ]
                )
                match template:
                    case "duras_trials/sweep.png":
                        logging.info("Dura's Trial already cleared")
                        return None
                    case "duras_trials/battle.png":
                        self.click(x, y)
                    case "battle/records.png":
                        pass

            result = self.handle_battle_screen(
                self.get_config().duras_trials.use_suggested_formations
            )

            if result is True and not nightmare_mode:
                self.wait_for_template("duras_trials/first_clear.png")
                next_button = self.find_template_match("next.png")
                if next_button is not None:
                    count += 1
                    logging.info(f"Trials pushed: {count}")
                    self.click(*next_button)
                    self.click(*next_button)
                    sleep(3)
                    continue
                else:
                    logging.info("Dura's Trial completed")
                    return None

            if result is True and nightmare_mode:
                count += 1
                logging.info(f"Nightmare Trials pushed: {count}")
                if self.find_template_match("duras_trials/continue_gray.png"):
                    logging.info("Nightmare Trial completed")
                    return None
                continue
            logging.info("Dura's Trial failed")
            return None
        return None

    def assist_synergy_corrupt_creature(self) -> None:
        self.start_up()
        assist_limit = self.get_config().general.assist_limit
        logging.info("Assisting Synergy and Corrupt Creature in world chat")
        count: int = 0
        while count < assist_limit:
            if self.__find_synergy_or_corrupt_creature():
                count += 1

        logging.info("Done assisting")
        return None

    def __find_synergy_or_corrupt_creature(self) -> bool:
        result = self.find_any_template(
            [
                "assist/world_chat.png",
                "assist/tap_to_enter.png",
                "assist/team-up_chat.png",
            ]
        )
        if result is None:
            logging.info("Opening chat")
            self.__navigate_to_default_state()
            self.click(1010, 1080, scale=True)
            sleep(1)
            self.click(110, 350, scale=True)
            return False

        template, x, y = result
        match template:
            case "assist/world_chat.png":
                self.click(260, 1400, scale=True)
            case "assist/tap_to_enter.png", "assist/team-up_chat.png":
                logging.info("Switching to world chat")
                self.click(110, 350, scale=True)
                return False

        try:
            template, x, y = self.wait_for_any_template(
                ["assist/join_now.png", "assist/synergy.png", "assist/chat_button.png"],
                delay=0.1,
                timeout=2,
            )
        except TimeoutException:
            return False
        if "assist/chat_button.png" == template:
            if self.find_template_match("assist/world_chat.png") is None:
                # Back button no longer reliable closes profile/chat windows
                # self.press_back_button()
                self.click(550, 100, scale=True)
                sleep(1)
            return False
        self.click(x, y)
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

        self.click(*ready)
        # Sometimes people wait forever for a third to join...
        self.wait_until_template_disappears(
            "assist/rewards_heart.png", timeout=self.BATTLE_TIMEOUT
        )
        self.wait_for_template("assist/bell.png")
        # click first 5 heroes in row 1 and 2
        for x in [110, 290, 470, 630, 800]:
            self.click(x, 1300, scale=True)
            sleep(0.5)
        while True:
            cc_ready = self.find_template_match("assist/cc_ready.png")
            if cc_ready:
                self.click(*cc_ready)
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
        self.click(*go)
        sleep(3)
        self.click(130, 900, scale=True)
        sleep(1)
        self.click(630, 1800, scale=True)
        return True

    def push_legend_trials(self) -> None:
        self.start_up()
        self.store[self.STORE_MODE] = self.MODE_LEGEND_TRIALS
        try:
            self.__navigate_to_legend_trials_select_tower()
        except TimeoutException as e:
            logging.error(f"{e}")
            return None

        towers = self.get_config().legend_trials.towers

        results = {}
        faction_paths = {
            "lightbearer": "legend_trials/swords_lightbearer.png",
            "wilder": "legend_trials/swords_wilder.png",
            "graveborn": "legend_trials/swords_graveborn.png",
            "mauler": "legend_trials/swords_mauler.png",
        }

        self.get_screenshot()
        for faction, path in faction_paths.items():
            if faction.capitalize() in towers:
                result = self.find_template_match(
                    path, threshold=0.975, use_previous_screenshot=True
                )
                if result is None:
                    logging.warning(
                        f"{faction.capitalize()}s Tower not available or not found"
                    )
                else:
                    results[faction] = result
            else:
                logging.info(f"{faction.capitalize()}s excluded in config")

        for faction, result in results.items():
            logging.info(f"Starting {faction.capitalize()} Tower")
            self.__navigate_to_legend_trials_select_tower()
            self.click(*result)
            try:
                self.__select_legend_trials_floor(faction)
            except (TimeoutException, NotFoundException) as e:
                logging.error(f"{e}")
                self.press_back_button()
                sleep(3)
                continue
            self.__handle_legend_trials_battle(faction)
        logging.info("Legend Trial finished")
        return None

    def __handle_legend_trials_battle(self, faction: str) -> None:
        count: int = 0
        while True:
            try:
                result = self.handle_battle_screen(
                    self.get_config().legend_trials.use_suggested_formations
                )
            except TimeoutException as e:
                logging.warning(f"{e}")
                return None

            if result is True:
                next_btn = self.wait_for_template("next.png")
                if next_btn is not None:
                    count += 1
                    logging.info(f"{faction.capitalize()} Trials pushed: {count}")
                    self.click(*next_btn)
                    continue
                else:
                    logging.warning(
                        "Not implemented assuming this shows up after the last floor?"
                    )
                    return None
            logging.info(f"{faction.capitalize()} Trials failed")
            return None
        return None

    def __select_legend_trials_floor(self, faction: str) -> None:
        logging.debug("__select_legend_trials_floor")
        _ = self.wait_for_template(f"legend_trials/tower_icon_{faction}.png")
        challenge_btn = self.wait_for_any_template(
            [
                "legend_trials/challenge_ch.png",
                "legend_trials/challenge_ge.png",
            ],
            threshold=0.8,
            grayscale=True,
            delay=0.5,
            timeout=6,
        )
        _, x, y = challenge_btn
        self.click(x, y)
        return None

    def __navigate_to_legend_trials_select_tower(self) -> None:
        def check_for_legend_trials_s_header() -> bool:
            header = self.find_template_match("legend_trials/s_header.png")
            return header is not None

        self.__navigate_to_default_state(
            check_callable=check_for_legend_trials_s_header
        )

        logging.info("Navigating to Legend Trials tower selection")
        s_header = self.find_template_match(
            "legend_trials/s_header.png", use_previous_screenshot=True
        )
        if not s_header:
            logging.info("Clicking Battle Modes button")
            self.click(460, 1830, scale=True)
            label = self.wait_for_template(
                "legend_trials/label.png",
                timeout_message="Could not find Legend Trial Label",
            )
            self.click(*label)
            self.wait_for_template(
                "legend_trials/s_header.png",
                timeout_message="Could not find Season Legend Trial Header",
            )
        sleep(1)
        return None

    def event_guild_chat_claim(self) -> NoReturn:
        self.start_up()
        logging.info("This claims rewards in Guild Chat (e.g. Happy Satchel)")
        logging.info("Opening chat")
        self.__navigate_to_default_state()
        self.click(1010, 1080, scale=True)
        sleep(3)
        while True:
            claim_button = self.find_template_match(
                "event/guild_chat_claim/claim_button.png"
            )
            if claim_button:
                self.click(*claim_button)
                # click again to close popup
                sleep(2)
                self.click(*claim_button)
            # switch to world chat and back because sometimes chat stops scrolling
            world_chat_icon = self.find_template_match(
                "event/guild_chat_claim/world_chat_icon.png"
            )
            if world_chat_icon:
                self.click(*world_chat_icon)
                sleep(1)
            guild_chat_icon = self.find_template_match(
                "event/guild_chat_claim/guild_chat_icon.png"
            )
            if guild_chat_icon:
                self.click(*guild_chat_icon)
            sleep(1)

    def event_monopoly_assist(self) -> NoReturn:
        self.start_up()
        logging.info("This assists friends on Monopoly board events to farm Pal-Coins")
        logging.warning("You have to open the Monopoly assists screen yourself")
        win_count = 0
        loss_count = 0
        while True:
            self.wait_for_template(
                "event/monopoly_assist/log.png",
                timeout=5,
                timeout_message="Monopoly assists screen not found",
            )

            next_assist: tuple[int, int] | None = None
            count = 0
            while next_assist is None:
                assists = self.find_all_template_matches(
                    "event/monopoly_assist/assists.png"
                )
                for assist in assists:
                    if count >= loss_count:
                        next_assist = assist
                        break
                    count += 1
                if next_assist is None:
                    self.swipe_down()

            self.click(*next_assist)
            sleep(3)
            try:
                if self.handle_battle_screen(use_suggested_formations=False):
                    win_count += 1
                    logging.info(f"Win #{win_count} Pal-Coins: {win_count*15}")
                else:
                    loss_count += 1
                    logging.warning(f"Loss #{loss_count}")
            except Exception as e:
                logging.error(f"{e}")
