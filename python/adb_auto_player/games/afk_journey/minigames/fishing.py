from time import sleep

import cv2
import numpy as np
from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.image_manipulation import crop
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions

from ..base import AFKJourneyBase
from ..gui_category import AFKJCategory

STRONG_PULL = Point(780, 1290)
DISTANCE_FOR_LONG_HOLD = 600
DISTANCE_FOR_MEDIUM_HOLD = 300


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
        # Disable debug screenshots we need to maximise speed
        # TODO maybe debug screenshots should be saved async?
        # But really do we need debug screenshots here?
        self.disable_debug_screenshots = True
        # self._start_minigame()
        self._fish()

    def _fish(self) -> None:
        print("Fishing...")
        try:
            btn = self.wait_for_any_template(
                ["fishing/hook_fish", "fishing/start_fishing"],
                crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
                timeout=self.MIN_TIMEOUT,
            )
        except GameTimeoutError:
            return

        # Check we are in the minigame
        book = self.game_find_template_match(
            "fishing/book.png",
            crop_regions=CropRegions(left=0.9, bottom=0.9),
        )

        if not book:
            return

        # Start fishing
        print("Start Fishing...")
        self.tap(btn, scale=True)
        sleep(1)
        _ = self.wait_for_template(
            "fishing/hook_fish",
            crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
            timeout=self.MIN_TIMEOUT,
            delay=0.1,
        )
        sleep(0.6)
        self.tap(btn, scale=True, blocking=False)
        _ = self.wait_for_any_template(
            [
                "fishing/hook",
                "fishing/hook_held",
            ],
            crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
            timeout=self.MIN_TIMEOUT,
            delay=0.1,
            threshold=ConfidenceValue("60%"),
        )
        print("Fishing Loop...")
        check_book_at = 20
        count = 0
        thread = None
        while True:
            count += 1
            screenshot = self.get_screenshot()
            if count % check_book_at == 0:
                if not thread or not thread.is_alive():
                    self.tap(STRONG_PULL, blocking=False)
                if self.game_find_template_match(
                    "fishing/book.png",
                    crop_regions=CropRegions(left=0.9, bottom=0.9),
                    screenshot=screenshot,
                ):
                    print("its joever")
                    break
            cropped = crop(
                screenshot,
                CropRegions(left=0.1, right=0.1, top="980px", bottom="740px"),
            )

            if not thread or not thread.is_alive():
                top, middle = _find_fishing_colors_fast(cropped.image)
                if top and middle and top > middle:
                    print("hold")
                    if top - middle > DISTANCE_FOR_LONG_HOLD:
                        thread = self.hold(btn, duration=1.5, blocking=False)
                    elif top - middle > DISTANCE_FOR_MEDIUM_HOLD:
                        thread = self.hold(btn, duration=1.0, blocking=False)
                    else:
                        thread = self.hold(btn, duration=0.5, blocking=False)
                else:
                    print("loose")

        return

    def _start_minigame(self) -> None:
        btn = self.game_find_template_match(
            "fishing/start_minigame.png", crop_regions=CropRegions(top=0.5, bottom=0.2)
        )
        if not btn:
            return
        self.tap(btn)
        sleep(5)
        # Intentionally fail the first
        self.wait_for_template("fishing/book.png")
        return


def _find_fishing_colors_fast(img: np.ndarray) -> tuple[int | None, int | None]:
    """Finds colors fast.

    Returns:
        x coordinate of the box, x coordinate of the hook
    """
    h, w = img.shape[:2]

    # Define thirds
    top_third = img[0 : h // 3, :]
    middle_third = img[h // 3 : 2 * h // 3, :]

    # === TOP THIRD: Find specific color RGB(244, 222, 105) ===
    target_color = np.array([105, 222, 244])  # BGR format
    tolerance = 15  # Adjust as needed

    # Create mask for target color with tolerance
    lower_bound = np.maximum(target_color - tolerance, 0)
    upper_bound = np.minimum(target_color + tolerance, 255)

    top_mask = cv2.inRange(top_third, lower_bound, upper_bound)

    # Find contours for bounding box
    contours, _ = cv2.findContours(top_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    top_result = None
    length_when_the_circle_is_almost_full = 140
    if contours:
        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w_box, h_box = cv2.boundingRect(largest_contour)
        top_result = (
            x + w_box // 2 if w_box > length_when_the_circle_is_almost_full else x
        )

    # === MIDDLE THIRD: Find icon with color range ===
    # Define color range in BGR
    lower_orange = np.array([58, 194, 250])  # RGB(250, 194, 58) -> BGR
    upper_orange = np.array([83, 212, 255])  # RGB(255, 212, 83) -> BGR

    # Create mask for orange range
    middle_mask = cv2.inRange(middle_third, lower_orange, upper_orange)

    # Find 50px wide section with most color occurrences
    best_x = 0
    max_count = 0

    # Slide 50px window across width
    window_width = 50
    for x in range(0, w - window_width + 1, 5):  # Step by 5 for speed
        window_mask = middle_mask[:, x : x + window_width]
        count = np.sum(window_mask > 0)

        if count > max_count:
            max_count = count
            best_x = x

    middle_result = best_x + window_width // 2 if max_count > 0 else None

    return top_result, middle_result
