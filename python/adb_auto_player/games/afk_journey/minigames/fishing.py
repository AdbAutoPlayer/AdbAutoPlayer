import logging
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
        if self._stream is None:
            logging.warning(
                "Quite frankly there is not a very good chance this will work "
                "without Device Streaming."
            )

        if self.get_scale_factor() != 1.0:
            logging.error(
                "Fishing is optimized for 1080x1920 it will not work with other "
                "resolutions."
            )
            return

        # Disable debug screenshots we need to maximise speed
        # TODO maybe debug screenshots should be saved async?
        # But really do we need debug screenshots here?
        self.disable_debug_screenshots = True

        self._warmup_cache_for_all_fishing_templates()

        # TODO needs map navigation logic
        # the _fish function only works inside of the fishing minigame
        # after navigation might be easier to intentionally fail the first time to be
        # inside the fishing screen and not the overworld.

        self._fish()

    def _warmup_cache_for_all_fishing_templates(self):
        templates = [
            "fishing/book.png",
            "fishing/hook.png",
            "fishing/hook_fish.png",
            "fishing/hook_held.png",
            "fishing/start_fishing.png",
        ]
        for template in templates:
            _ = self._load_image(template)

    def _i_am_in_the_fishing_screen(self) -> bool:
        try:
            _ = self.wait_for_any_template(
                ["fishing/hook_fish", "fishing/start_fishing"],
                crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
                timeout=self.MIN_TIMEOUT,
            )
        except GameTimeoutError:
            return False

        # Check we are in the minigame
        book = self.game_find_template_match(
            "fishing/book.png",
            crop_regions=CropRegions(left=0.9, bottom=0.9),
        )

        if not book:
            return False
        return True

    def _fish(self) -> None:
        if not self._i_am_in_the_fishing_screen():
            logging.error("Not in Fishing screen")
            return

        btn = self.wait_for_any_template(
            ["fishing/hook_fish", "fishing/start_fishing"],
            crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
            timeout=self.MIN_TIMEOUT,
            timeout_message="Cast Fishing Rod Button not found",
        )

        self.tap(btn)
        sleep(1)
        _ = self.wait_for_template(
            "fishing/hook_fish",
            crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
            timeout=self.MIN_TIMEOUT,
            delay=0.1,
        )
        sleep(0.6)
        self.tap(btn, blocking=False)

        # TODO This part is a bit sus. Needs to be double checked.
        try:
            _ = self.wait_for_any_template(
                [
                    "fishing/hook",
                    "fishing/hook_held",
                ],
                crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
                timeout=self.MIN_TIMEOUT,
                delay=0.05,
                threshold=ConfidenceValue("60%"),
            )
        except GameTimeoutError:
            logging.info("Small fish caught.")

        # Fishing Loop
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
                    # TODO Not sure how to detect a catch or loss here.
                    # Might have to OCR the remaining attempts?
                    break
            cropped = crop(
                screenshot,
                CropRegions(left=0.1, right=0.1, top="980px", bottom="740px"),
            )

            if not thread or not thread.is_alive():
                top, middle = _find_fishing_colors_fast(cropped.image)
                if top and middle and top > middle:
                    print("hold")
                    # TODO values need to be adjusted, duration could be adjusted.
                    # Constants for distance can be adjusted too.
                    if top - middle > DISTANCE_FOR_LONG_HOLD:
                        thread = self.hold(btn, duration=1.5, blocking=False)
                    elif top - middle > DISTANCE_FOR_MEDIUM_HOLD:
                        thread = self.hold(btn, duration=1.0, blocking=False)
                    else:
                        thread = self.hold(btn, duration=0.5, blocking=False)
                else:
                    # TODO remove all those print statements when done
                    print("loose")

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
    # bottom third is not needed, but I will keep it like this

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
        # This is a bit sketchy
        # The fishing circle box starts at the top middle so at the start you will
        # Want the left most x-coordinate (x)
        # When the circle is almost full it should wrap, and you want the middle.
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
    for x in range(0, w - window_width + 1, 5):  # Step by 5 for 5x speed
        window_mask = middle_mask[:, x : x + window_width]
        count = np.sum(window_mask > 0)

        if count > max_count:
            max_count = count
            best_x = x

    middle_result = best_x + window_width // 2 if max_count > 0 else None

    return top_result, middle_result
