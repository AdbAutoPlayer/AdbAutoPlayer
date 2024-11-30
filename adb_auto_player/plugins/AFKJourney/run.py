import adb_auto_player.logger as logging
from time import sleep
from typing import Dict, Any, NoReturn
from adbutils._device import AdbDevice
from adb_auto_player.plugin import Plugin


class AFKJourney(Plugin):
    BATTLE_TIMEOUT: int = 180

    def get_template_dir_path(self) -> str:
        return "plugins/AFKJourney/templates"

    def get_afk_stage_config(self) -> tuple[int, int, bool]:
        formations = int(self.config.get("afk_stages", {}).get("formations", 7))
        formations = min(formations, 7)
        formations = max(formations, 1)

        attempts = int(self.config.get("afk_stages", {}).get("attempts", 5))
        attempts = min(attempts, 5)
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
        self.__handle_multi_stage()
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
            if self.find_template_center("formation_swap.png") is None:
                is_multi_stage = False

            if use_suggested_formations:
                self.__copy_suggested_formation(formation_num)

            if is_multi_stage and self.__handle_multi_stage():
                return True

            if not is_multi_stage and self.__handle_single_stage():
                return True

        logging.info("Stopping Battle, tried all attempts for all Formations")
        return False

    def __copy_suggested_formation(self, formation_num: int = 1) -> None | NoReturn:
        logging.info(f"Copying Formation #{formation_num}")
        x, y = self.wait_for_template("records.png")
        self.device.click(x, y)

        while formation_num > 1:
            x, y = self.wait_for_template(
                "formation_next.png",
                timeout=5,
                exit_message=f"Formation #{formation_num} not found",
            )
            self.device.click(x, y)
            sleep(1)
            formation_num -= 1

        x, y = self.wait_for_template("copy.png", timeout=5)
        self.device.click(x, y)
        logging.debug("Formation copied")
        return None

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
            result = self.find_template_center("multi_stage_first_victory.png")
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
                x, y = self.wait_for_template(
                    "continue.png",
                    timeout=self.BATTLE_TIMEOUT,
                )
                self.device.click(x, y)
                self.wait_for_template("records.png")
                if self.find_template_center("multi_stage_first_victory.png") is None:
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

        if self.find_template_center("spend.png") and not spend_gold:
            return False

        self.__click_confirm_on_popup()
        self.__click_confirm_on_popup()

        return True

    def __click_confirm_on_popup(self) -> None:
        result = self.find_template_center("confirm.png")
        if result:
            x, y = result
            self.device.click(x, y)
            sleep(1)

    def __return_to_afk_select_to_clear_first_win_formation(self) -> None:
        self.wait_for_template("records.png")
        sleep(1)
        logging.info("Returning to AFK Stages select")
        self.press_back_button()
        x, y = self.wait_for_template("confirm.png")
        self.device.click(x, y)

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
            if self.find_template_center("time_of_day.png") is None:
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
        self.__handle_dura_screen(y=1300)
        logging.info("Trying other Trial.")
        self.__navigate_to_duras_trials_screen()
        self.__handle_dura_screen(y=1550)
        return None

    def __navigate_to_duras_trials_screen(self) -> None | NoReturn:
        logging.info("Navigating to default state")
        self.__navigate_to_default_state()
        logging.info("Clicking Battle Modes button")
        self.device.click(460, 1830)
        x, y = self.wait_for_template(
            "duras_trials.png", exit_message="Could not find Dura's Trials"
        )
        self.device.click(x, y)
        return None

    def __handle_dura_screen(self, y: int) -> None | NoReturn:
        _, use_suggested_formations = self.get_duras_trials_config()
        x, _ = self.wait_for_template("rate_up.png", grayscale=True)
        self.device.click(x, y)
        template, x, y = self.wait_for_any_template(["battle.png", "sweep.png"])

        match template:
            case "sweep.png":
                logging.info("Dura Trial already finished returning.")
                return None
            case "battle.png":
                self.device.click(x, y)
                self.handle_battle_screen(use_suggested_formations)

        return None


def execute(device: AdbDevice, config: Dict[str, Any]) -> None | NoReturn:
    game = AFKJourney(device, config)

    game.check_requirements()

    sleep(1)

    menu(game)

    return None


def menu(game: AFKJourney) -> None | NoReturn:
    while True:
        print("Select an option:")
        print("[1] Push Season Talent Stages")
        print("[2] Push AFK Stages")
        print("[3] Push Duras Trials")
        print("[4] Fight Battle - use suggested Formations")
        print("[5] Fight Battle - use your own Formation")
        print("[9] Test")
        print("[0] Exit")

        choice = input(">> ")

        match choice:
            case "1":
                game.push_afk_stages(season=True)
            case "2":
                game.push_afk_stages(season=False)
            case "3":
                game.push_duras_trials()
            case "4":
                game.handle_battle_screen(use_suggested_formations=True)
            case "5":
                game.handle_battle_screen(use_suggested_formations=False)
            case "9":
                game.test()
            case "0":
                print("Exiting...")
                break
            case _:
                print("Invalid choice, please try again")
        sleep(3)

    return None
