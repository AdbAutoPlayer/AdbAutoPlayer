from time import sleep
from typing import Dict, Any

from adbutils._device import AdbDevice

import adb_auto_player.screen_utils as screen_utils
from adb_auto_player.plugin import Plugin


class AFKJourney(Plugin):
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

    def navigate_to_default_state(self) -> None:
        while True:
            if (
                screen_utils.find_center(
                    self.device, "plugins/AFKJourney/images/time_of_day_button.png"
                )
                is None
            ):
                self.device.keyevent(4)
                sleep(3)
            else:
                break

    def push_afk_stages(self, season: bool) -> None:
        formations, attempts, push_both_modes = self.get_afk_stage_config()

        self.navigate_to_default_state()
        # TODO click bottom left cornerLDPlayer 9
        # TODO check key element is visible
        if season:
            # click season trials
            pass
        else:
            # click afk stage
            pass
        # check key element is visible
        # click records
        # copy formation
        # ...


def execute(device: AdbDevice, config: Dict[str, Any]) -> None:
    game = AFKJourney(device, config)

    game.check_requirements()

    sleep(1)

    while True:
        print("Select an option:")
        print("[1] Push AFK Stages")
        print("[2] Push Season Talent Stages")
        print("[3] Exit")

        choice = input(">> ")

        if choice == "1":
            game.push_afk_stages(season=False)
            break
        elif choice == "2":
            game.push_afk_stages(season=True)
            break
        elif choice == "3":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")
