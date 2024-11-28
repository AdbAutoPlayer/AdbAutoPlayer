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

    def navigate_to_default_state(self) -> None:
        while True:
            if self.find_template_center("time_of_day.png") is None:
                self.device.keyevent(4)
                sleep(3)
            else:
                break

    def copy_formation(self, formation_num: int = 1) -> None:
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
        logging.info("Formation copied")

    def test(self) -> None | NoReturn:
        self.wait_for_any_template(
            ["first_clear.png", "retry.png"], timeout=self.BATTLE_TIMEOUT
        )
        # need to refactor this here so
        # the wait_for_any_template function should not take separate screencaps
        template, x, y = self.wait_for_any_template(
            ["first_clear.png", "retry.png"], timeout=self.BATTLE_TIMEOUT
        )
        match template:
            case "first_clear.png":
                # return True
                logging.critical_and_exit("Congrats :) Feature WIP")
            case "retry.png":
                self.device.click(x, y)
            case _:
                # return True
                logging.critical_and_exit("Congrats :) Feature WIP")

        return None

    def handle_battle(self, is_multi_stage: bool = False) -> bool | NoReturn:
        _, attempts, _ = self.get_afk_stage_config()
        spend_gold = self.get_duras_trials_config()

        count: int = 0

        while count < attempts:
            count += 1

            self.wait_for_template("records.png")
            logging.info(f"Starting Battle #{count}")
            self.device.click(550, 1780)
            self.wait_until_template_disappears("records.png")

            sleep(1)

            if self.find_template_center("spend.png") and not spend_gold:
                logging.critical_and_exit("Stopping attempts config: spend_gold=false")

            result = self.find_template_center("confirm_battle.png")
            if result:
                x, y = result
                self.device.click(x, y)

            if is_multi_stage:
                logging.critical_and_exit("Not Implemented :(")

            template, x, y = self.wait_for_any_template(
                ["first_clear.png", "retry.png"], timeout=self.BATTLE_TIMEOUT
            )

            match template:
                case "first_clear.png":
                    # return True
                    logging.critical_and_exit("Congrats :) Feature WIP")
                case "retry.png":
                    self.device.click(x, y)
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

        while formation_num < formations:
            formation_num += 1
            self.wait_for_template("records.png")

            is_multi_stage: bool = True
            if self.find_template_center("formation_swap.png") is None:
                is_multi_stage = False

            if not use_your_own_formation:
                self.copy_formation(formation_num)

            if self.handle_battle(is_multi_stage):
                return True

        logging.critical_and_exit("Tried all attempts for all Formations")

    def navigate_to_afk_stages_screen(self, season: bool) -> None:
        logging.info("Navigating to default state")
        self.navigate_to_default_state()
        logging.info("Clicking AFK Progress button")
        self.device.click(90, 1830)
        sleep(3)

        # TODO Handle afk rewards popup

        if season:
            logging.info("Clicking Talent Trials button")
            self.device.click(300, 1610)
        else:
            logging.info("Battle button")
            self.device.click(800, 1610)

    def push_afk_stages(self, season: bool) -> None:
        _, _, push_both_modes = self.get_afk_stage_config()

        self.navigate_to_afk_stages_screen(season=season)
        while self.handle_battle_screen():
            pass

        if push_both_modes:
            self.navigate_to_afk_stages_screen(season=not season)
            while self.handle_battle_screen():
                pass


def execute(device: AdbDevice, config: Dict[str, Any]) -> None:
    game = AFKJourney(device, config)

    game.check_requirements()

    sleep(1)

    menu(game)


def menu(game: AFKJourney) -> None:
    print("Select an option:")
    print("[1] Push AFK Stages (DOES NOT WORK YET)")
    print("[2] Push Season Talent Stages (DOES NOT WORK YET)")
    print("[3] Fight Battle - use suggested Formations")
    print("[4] Fight Battle - use your own Formation")
    print("[5] Test - Ignore This")
    print("[0] Exit")

    choice = input(">> ")

    if choice == "1":
        game.push_afk_stages(season=False)
        return
    elif choice == "2":
        game.push_afk_stages(season=True)
        return
    elif choice == "3":
        game.handle_battle_screen()
        return
    elif choice == "4":
        game.handle_battle_screen(use_your_own_formation=True)
        return
    elif choice == "5":
        game.test()
        return
    elif choice == "0":
        print("Exiting...")
        return
    else:
        print("Invalid choice, please try again")
