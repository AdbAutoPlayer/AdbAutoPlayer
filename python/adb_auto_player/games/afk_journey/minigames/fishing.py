import threading
from time import sleep

import cv2
from PIL.ImageChops import screen

from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.image_manipulation import crop
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from ..base import AFKJourneyBase
from ..gui_category import AFKJCategory

STRONG_PULL = Point(780, 1290)


class Fishing(AFKJourneyBase):
    """Fishing."""

    @register_command(
        gui=GUIMetadata(
            label="Fishing",
            category=AFKJCategory.EVENTS_AND_OTHER,
        ),
    )
    def fishing(self) -> None:
        self.start_up(device_streaming=True)
        self._start_minigame()
        self._fish()



    def _fish(self) -> None:
        try:
            btn = self.wait_for_any_template(
                [
                    "fishing/hook_fish",
                    "fishing/start_fishing"
                ],
                crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
                timeout=self.MIN_TIMEOUT,
            )
        except GameTimeoutError:
            return

        if self.game_find_template_match(
            "fishing/book.png"
        ):
            self.tap(btn, scale=True)
            sleep(1)
            _ = self.wait_for_template(
                "fishing/hook_fish",
                crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
                timeout=self.MIN_TIMEOUT,
            )



        check_book_at = 10
        count = 0
        #             self.tap(STRONG_PULL)
        while True:
            count += 1
            screenshot = self.get_screenshot()
            if count % check_book_at == 0:
                if self.game_find_template_match(
                    "fishing/book.png",
                    crop_regions=CropRegions(left=0.9, bottom=0.9),
                    screenshot=screenshot,
                ):
                    break
            cropped = crop(
                screenshot,
                CropRegions(
                    left=0.1, right=0.1, top=0.5, bottom=0.35
                )
            )
            # TODO heatmap or find most yellow/orange colors

            self.hold(btn)
            sleep(0.5)

        return


    def _start_minigame(self) -> None:
        if btn := self.game_find_template_match(
            "fishing/start_minigame.png",
            crop_regions=CropRegions(top=0.5, bottom=0.2)
        ):
            self.tap(btn)
            sleep(1)
        return