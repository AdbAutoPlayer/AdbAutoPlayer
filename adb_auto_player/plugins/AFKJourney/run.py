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

    def get_duras_trials_config(self) -> bool:
        spend_gold = bool(self.config.get("duras_trials", {}).get("spend_gold", False))

        return spend_gold

    def click_confirm(self) -> None:
        result = self.find_template_center("confirm.png")
        if result:
            x, y = result
            self.device.click(x, y)

    def navigate_to_default_state(self) -> None:
        while True:
            if self.find_template_center("time_of_day.png") is None:
                self.press_back_button()
                sleep(3)
            else:
                break

    def copy_formation(self, formation_num: int = 1) -> None | NoReturn:
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

    def test(self) -> NoReturn:
        self.handle_multi_stage()
        logging.critical_and_exit(":)")

    def start_battle(self) -> None | NoReturn:
        spend_gold = self.get_duras_trials_config()

        self.wait_for_template("records.png")
        self.device.click(850, 1780)
        self.wait_until_template_disappears("records.png")
        sleep(1)

        if self.find_template_center("spend.png") and not spend_gold:
            logging.critical_and_exit("Stopping attempts config: spend_gold=false")

        self.click_confirm()
        return None

    def handle_multi_stage(self) -> bool | NoReturn:
        _, attempts, _ = self.get_afk_stage_config()

        count: int = 0
        count_stage_2: int = 0

        while True:
            self.wait_for_template(
                "records.png",
                timeout=self.BATTLE_TIMEOUT,
            )
            result = self.find_template_center("multi_stage_first_victory.png")

            is_stage_2: bool = False
            if result is None:
                count += 1
                logging.info(f"Starting Battle #{count} vs Team 1")
            else:
                count_stage_2 += 1
                logging.info(f"Starting Battle #{count_stage_2} vs Team 2")
                is_stage_2 = True

            self.start_battle()

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
                self.press_back_button()
                sleep(3)
                self.click_confirm()
                self.select_afk_stage()
                return False

    def handle_single_stage(self) -> bool | NoReturn:
        _, attempts, _ = self.get_afk_stage_config()

        count: int = 0

        while count < attempts:
            count += 1

            logging.info(f"Starting Battle #{count}")
            self.start_battle()

            template, x, y = self.wait_for_any_template(
                ["first_clear.png", "retry.png"],
                timeout=self.BATTLE_TIMEOUT,
            )

            match template:
                case "first_clear.png":
                    # return True
                    logging.critical_and_exit("Congrats :) Feature WIP")
                case "retry.png":
                    logging.info(f"Lost Battle #{count}")
                    self.device.click(x, y)
                    return False
                case _:
                    # return True
                    logging.critical_and_exit("Congrats :) Feature WIP")

        logging.info("Lost all Battles with current Formation")
        return False

    def handle_battle_screen(
        self, use_your_own_formation: bool = False
    ) -> bool | NoReturn:
        formations, _, _ = self.get_afk_stage_config()
        formation_num: int = 0
        if use_your_own_formation:
            formations = 1

        logging.info("Starting new Stage or Trial")

        while formation_num < formations:
            formation_num += 1
            self.wait_for_template("records.png")

            is_multi_stage: bool = True
            if self.find_template_center("formation_swap.png") is None:
                is_multi_stage = False

            if not use_your_own_formation:
                self.copy_formation(formation_num)

            if is_multi_stage and self.handle_multi_stage():
                return True

            if not is_multi_stage and self.handle_single_stage():
                return True

        logging.critical_and_exit("Tried all attempts for all Formations")

    def navigate_to_afk_stages_screen(self) -> None:
        logging.info("Navigating to default state")
        self.navigate_to_default_state()
        logging.info("Navigating to AFK Stage Battle screen")
        self.device.click(90, 1830)
        self.select_afk_stage()

    def select_afk_stage(self) -> None:
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

    def navigate_to_duras_trials_screen(self) -> None | NoReturn:
        logging.info("Navigating to default state")
        self.navigate_to_default_state()
        logging.info("Clicking Battle Modes button")
        self.device.click(460, 1830)
        x, y = self.wait_for_template(
            "duras_trials.png", exit_message="Could not find Dura's Trials"
        )
        self.device.click(x, y)
        return None

    def handle_dura_screen(self, y: int) -> NoReturn:
        x, _ = self.wait_for_template("rate_up.png", grayscale=True)
        self.device.click(x, y)
        sleep(3)
        logging.critical_and_exit("WIP")
        # TODO check if max yes return
        # TODO press battle button
        # self.handle_single_stage()

    def push_duras_trials(self) -> NoReturn:
        self.navigate_to_duras_trials_screen()
        self.handle_dura_screen(y=1300)

        self.press_back_button()
        self.handle_dura_screen(y=1550)

    def get_current_afk_stages_name(self) -> str:
        season = self.store.get("season", False)
        if season:
            return "Season Talent Stages"

        return "AFK Stages"

    def push_afk_stages(self, season: bool) -> None | NoReturn:
        _, _, push_both_modes = self.get_afk_stage_config()
        self.store["season"] = season

        self.start_afk_stage()
        if push_both_modes:
            self.store["season"] = not season
            self.start_afk_stage()

        return None

    def start_afk_stage(self) -> None | NoReturn:
        stages_pushed: int = 0
        stages_name = "AFK Stages"
        if self.store.get("season", False):
            stages_name = "Season Talent Stages"

        self.navigate_to_afk_stages_screen()
        while self.handle_battle_screen():
            stages_pushed += 1
            logging.info(f"{stages_name} pushed: {stages_pushed}")

        return None


def execute(device: AdbDevice, config: Dict[str, Any]) -> None | NoReturn:
    game = AFKJourney(device, config)

    game.check_requirements()

    sleep(1)

    menu(game)

    return None


def menu(game: AFKJourney) -> None | NoReturn:
    print("Select an option:")
    print("[1] Push Season Talent Stages")
    print("[2] Push AFK Stages")
    print("[3] Push Duras Trials (WIP)")
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
            game.handle_battle_screen()
        case "5":
            game.handle_battle_screen(use_your_own_formation=True)
        case "9":
            game.test()
        case "0":
            print("Exiting...")
        case _:
            print("Invalid choice, please try again")

    return None
