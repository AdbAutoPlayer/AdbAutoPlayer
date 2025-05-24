import logging
from time import sleep

from adb_auto_player import Coordinates, CropRegions
from adb_auto_player.decorators.register_custom_routine_choice import (
    register_custom_routine_choice,
)
from adb_auto_player.exceptions import GameActionFailedError
from adb_auto_player.games.afk_journey.base import AFKJourneyBase


class LevelUpAllHeroes(AFKJourneyBase):
    @register_custom_routine_choice("Level Up All Heroes")
    def _level_up_all_heroes(self) -> None:
        self.start_up(device_streaming=True)
        self._navigate_to_resonating_hall()
        while level_up_all_button := self.game_find_template_match(
            "resonating_hall/level_up_all.png",
            crop=CropRegions(left=0.3, right=0.3, top=0.7),
            threshold=0.95,
        ):
            for _ in range(10):
                self.tap(Coordinates(*level_up_all_button), blocking=False)
        logging.info("Level Up All Heroes not available.")
        sleep(3)  # wait for taps to finish

    def _navigate_to_resonating_hall(self) -> None:
        self._navigate_to_default_state()

        logging.debug("Navigating to the Resonating Hall.")
        max_click_count = 3
        click_count = 0
        while self._can_see_time_of_day_button():
            self.click(Coordinates(620, 1830), scale=True)
            sleep(3)
            click_count += 1
            if click_count > max_click_count:
                raise GameActionFailedError(
                    "Failed to navigate to the Resonating Hall."
                )
        _ = self.wait_for_any_template(
            templates=[
                "resonating_hall/artifacts.png",
                "resonating_hall/collections.png",
                "resonating_hall/equipment.png",
            ]
        )

    def _can_see_time_of_day_button(self):
        return (
            self.game_find_template_match(
                "time_of_day.png", crop=CropRegions(left=0.6, right=0.1, bottom=0.8)
            )
            is not None
        )
