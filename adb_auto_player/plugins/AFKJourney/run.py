from time import sleep
from typing import Any, NoReturn

from adbutils._device import AdbDevice

import adb_auto_player.logger as logging
from adb_auto_player.plugin import Plugin


class AFKJourney(Plugin):
    BATTLE_TIMEOUT: int = 180

    def get_template_dir_path(self) -> str:
        return "plugins/AFKJourney/templates"

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
                "label": "Fight Battle using suggested Formations",
                "action": self.handle_battle_screen,
                "kwargs": {"use_suggested_formations": True},
            },
            {
                "label": "Fight Battle using your own Formation",
                "action": self.handle_battle_screen,
                "kwargs": {"use_suggested_formations": False},
            },
            # I already finished this so I can't test to implement it.
            # {
            #    "label": "Season Legend Trial",
            #    "action": self.push_season_legend_trials,
            #    "kwargs": {},
            # },
            {
                "label": "Test",
                "action": self.test,
                "kwargs": {},
            },
        ]

    def get_general_config(self) -> list[str]:
        excluded_heroes: list[str] = self.config.get("general", {}).get(
            "excluded_heroes", []
        )
        return excluded_heroes

    def get_afk_stage_config(self) -> tuple[int, int, bool]:
        formations = int(self.config.get("afk_stages", {}).get("formations", 7))
        formations = min(formations, 7)
        formations = max(formations, 1)

        attempts = int(self.config.get("afk_stages", {}).get("attempts", 5))
        attempts = min(attempts, 100)
        attempts = max(attempts, 1)

        push_both_modes = bool(
            self.config.get("afk_stages", {}).get("push_both_modes", True)
        )
        return formations, attempts, push_both_modes

    def get_duras_trials_config(self) -> tuple[bool, bool]:
        spend_gold = bool(self.config.get("duras_trials", {}).get("spend_gold", False))
        use_suggested_formations = bool(
            self.config.get("duras_trials", {}).get("use_suggested_formations", True)
        )

        return spend_gold, use_suggested_formations

    def test(self) -> NoReturn:
        logging.critical_and_exit(":)")

    def handle_battle_screen(
        self, use_suggested_formations: bool = True
    ) -> bool | NoReturn:
        """
        Handles logic for battle screen
        :param use_suggested_formations: if False use suggested formations from records
        :return:
        """
        formations, _, _ = self.get_afk_stage_config()
        formation_num: int = 0
        if not use_suggested_formations:
            logging.info("Not using suggested Formations")
            formations = 1

        while formation_num < formations:
            formation_num += 1
            self.wait_for_template("records.png")

            is_multi_stage: bool = True
            if self.find_first_template_center("formation_swap.png") is None:
                is_multi_stage = False

            if use_suggested_formations and not self.__copy_suggested_formation(
                formation_num
            ):
                continue

            if is_multi_stage and self.__handle_multi_stage():
                return True

            if not is_multi_stage and self.__handle_single_stage():
                return True

        logging.info("Stopping Battle, tried all attempts for all Formations")
        return False

    def __copy_suggested_formation(self, formation_num: int = 1) -> int | NoReturn:
        logging.info(f"Copying Formation #{formation_num}")
        records = self.wait_for_template("records.png")
        self.device.click(*records)

        while formation_num > 1:
            formation_next = self.wait_for_template(
                "formation_next.png",
                timeout=5,
                exit_message=f"Formation #{formation_num} not found",
            )
            self.device.click(*formation_next)
            sleep(1)
            formation_num -= 1

        copy = self.wait_for_template("copy.png", timeout=5)

        excluded_hero = self.__formation_contains_excluded_hero()

        self.device.click(*copy)
        logging.debug("Formation copied")
        sleep(1)

        if self.__click_confirm_on_popup():
            logging.warning("Formation contains locked Artifacts or Heroes skipping")
            return False

        if excluded_hero is not None:
            logging.warning(
                f"Formation contains excluded Hero: '{excluded_hero}' skipping"
            )
            return False

        return True

    def __formation_contains_excluded_hero(self) -> str | None:
        excluded_heroes = self.get_general_config()
        excluded_heroes_dict = {
            f"heroes/{name.lower().replace(" ", "")}.png": name
            for name in excluded_heroes
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

    def __handle_multi_stage(self) -> bool | NoReturn:
        _, attempts, _ = self.get_afk_stage_config()
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

            if not self.start_battle():
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
                ["result.png", "continue.png"],
                timeout=self.BATTLE_TIMEOUT,
            )

            match template:
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

    def start_battle(self) -> bool | NoReturn:
        spend_gold, _ = self.get_duras_trials_config()

        self.wait_for_template("records.png")
        self.device.click(850, 1780)
        self.wait_until_template_disappears("records.png")
        sleep(1)

        if self.find_first_template_center("spend.png") and not spend_gold:
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

    def __handle_single_stage(self) -> bool | NoReturn:
        _, attempts, _ = self.get_afk_stage_config()
        count: int = 0

        while count < attempts:
            count += 1

            logging.info(f"Starting Battle #{count}")
            if not self.start_battle():
                return False

            template, x, y = self.wait_for_any_template(
                ["first_clear.png", "retry.png"],
                timeout=self.BATTLE_TIMEOUT,
            )

            match template:
                case "first_clear.png":
                    return True
                case "retry.png":
                    logging.info(f"Lost Battle #{count}")
                    self.device.click(x, y)
        return False

    def push_afk_stages(self, season: bool) -> None | NoReturn:
        """
        Entry for pushing AFK Stages
        :param season: Push Season Stage if True otherwise push regular AFK Stages
        """
        _, _, push_both_modes = self.get_afk_stage_config()
        self.store["season"] = season

        self.__start_afk_stage()
        if push_both_modes:
            self.store["season"] = not season
            self.__start_afk_stage()

        return None

    def __start_afk_stage(self) -> None | NoReturn:
        stages_pushed: int = 0
        stages_name = self.__get_current_afk_stages_name()

        logging.info(f"Pushing: {stages_name}")
        self.__navigate_to_afk_stages_screen()
        while self.handle_battle_screen():
            stages_pushed += 1
            logging.info(f"{stages_name} pushed: {stages_pushed}")

        return None

    def __get_current_afk_stages_name(self) -> str:
        season = self.store.get("season", False)
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
            else:
                break

    def __select_afk_stage(self) -> None:
        self.wait_for_template("resonating_hall.png")
        self.device.click(550, 1080)  # click rewards popup
        sleep(1)
        if self.store.get("season", False):
            logging.debug("Clicking Talent Trials button")
            self.device.click(300, 1610)
        else:
            logging.debug("Clicking Battle button")
            self.device.click(800, 1610)

        return None

    def push_duras_trials(self) -> None | NoReturn:
        """
        Entry for pushing Dura's Trials
        :return:
        """
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

    def __navigate_to_duras_trials_screen(self) -> None | NoReturn:
        logging.info("Navigating to Dura's Trial select")
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
                    "duras_trials.png", exit_message="Could not find Dura's Trials"
                )
                self.device.click(*duras_trials_label)
            case "rate_up.png":
                pass
        return None

    def __handle_dura_screen(self, x: int, y: int) -> None | NoReturn:
        _, use_suggested_formations = self.get_duras_trials_config()
        # y+100 clicks closer to center of the button instead of rate up text
        self.device.click(x, y + 100)
        template, x, y = self.wait_for_any_template(["battle.png", "sweep.png"])

        match template:
            case "sweep.png":
                logging.info("Dura Trial already finished returning")
                return None
            case "battle.png":
                self.device.click(x, y)
                self.handle_battle_screen(use_suggested_formations)

        return None


def execute(device: AdbDevice, config: dict[str, Any]) -> None | NoReturn:
    game = AFKJourney(device, config)

    game.check_requirements()

    sleep(1)

    game.run_cli_menu()

    return None
