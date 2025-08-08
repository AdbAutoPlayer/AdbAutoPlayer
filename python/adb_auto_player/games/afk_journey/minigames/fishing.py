import logging
import threading
import time
from time import sleep

import cv2
import numpy as np
from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import GameTimeoutError
from adb_auto_player.image_manipulation import Cropping
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Coordinates, Point, PointOutsideDisplay
from adb_auto_player.models.image_manipulation import CropRegions

from ..base import AFKJourneyBase

STRONG_PULL = Point(780, 1290)
DISTANCE_600 = 600
DISTANCE_400 = 400
DISTANCE_200 = 200
DISTANCE_100 = 100
DISTANCE_50 = 50
MAX_AVG_INPUT_DELAY_IN_MS = 200  # TODO Change to a reasonable value later
MAX_AVG_INPUT_DELAY_CANDIDATE = 100
MAX_SCREENSHOT_DELAY_IN_MS = 100  # TODO Change to a reasonable value later
MAX_AVG_SCREENSHOT_DELAY_CANDIDATE = 10
FISHING_DELAY = 1.0 / 30.0  # 1 Frame this is used for the fishing loop
# without CPU usage will go crazy
# could potentially be reduced to 1.0 / 60.0 if device streaming at 60 fps


class Fishing(AFKJourneyBase):
    """Fishing."""

    @register_command(
        # TODO expose in GUI when its done
        # gui=GUIMetadata(
        #     label="Fishing",
        #     category=AFKJCategory.EVENTS_AND_OTHER,
        # ),
    )
    def fishing(self) -> None:
        self.start_up(device_streaming=True)
        if self._stream is None:
            logging.warning(
                "Quite frankly there is not a very good chance this will work "
                "without Device Streaming."
            )

        if self.scale_factor != 1.0:
            logging.error(
                "Fishing is optimized for 1080x1920 it will not work with other "
                "resolutions."
            )
            return

        # Debug Screenshots need to be disabled.
        # IO will add a delay of anywhere between 50-300ms, generally speaking
        self.disable_debug_screenshots = True

        self._warmup_cache_for_all_fishing_templates()

        if (
            not self._passed_input_delay_check()
            or not self._passed_screenshot_delay_check()
        ):
            return

        # TODO needs map navigation logic
        # the _fish function only works inside of the fishing minigame
        # after navigation might be easier to intentionally fail the first time to be
        # inside the fishing screen and not the overworld.

        if not self._i_am_in_the_fishing_screen():
            logging.error("Not in Fishing screen")
            return

        while self._i_am_in_the_fishing_screen():
            self._fish()

    def _warmup_cache_for_all_fishing_templates(self):
        templates = [
            "fishing/book.png",
            "fishing/hook.png",
            "fishing/hook_fish.png",
            "fishing/hook_fish_big.png",
            "fishing/hook_held.png",
            "fishing/fishing_rod.png",
            "fishing/fishing_rod_big.png",
        ]
        for template in templates:
            _ = self._load_image(template)

    def _i_am_in_the_fishing_screen(self, is_quest_fishing_spot: bool = True) -> bool:
        try:
            _ = self.wait_for_any_template(
                [
                    "fishing/hook_fish",
                    "fishing/hook_fish_big",
                    "fishing/fishing_rod",
                    "fishing/fishing_rod_big",
                ],
                timeout=self.MIN_TIMEOUT,
                threshold=ConfidenceValue("70%"),
                crop_regions=CropRegions(
                    top="50%",
                    bottom="10%",
                    left="30%",
                    right="30%",
                ),
            )
        except GameTimeoutError:
            return False

        # Check we are in the regular minigame
        if not is_quest_fishing_spot:
            return (
                self.game_find_template_match(
                    "fishing/book.png",
                    crop_regions=CropRegions(left=0.9, bottom=0.9),
                    threshold=ConfidenceValue("70%"),
                )
                is not None
            )
        return True

    def _fish(self) -> None:
        if not self._i_am_in_the_fishing_screen():
            return

        btn = self.wait_for_any_template(
            [
                "fishing/hook_fish",
                "fishing/hook_fish_big",
                "fishing/fishing_rod",
                "fishing/fishing_rod_big",
            ],
            crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
            timeout=self.MIN_TIMEOUT,
            timeout_message="Cast Fishing Rod Button not found",
            threshold=ConfidenceValue("70%"),
        )

        # TODO could use some code so it always hit the middle in the pull size slider
        self.tap(btn)
        sleep(1)
        _ = self.wait_for_any_template(
            templates=[
                "fishing/hook_fish",
                "fishing/hook_fish_big",
            ],
            crop_regions=CropRegions(left=0.3, right=0.3, top=0.5, bottom=0.2),
            timeout=self.MIN_TIMEOUT,
            delay=0.1,
            threshold=ConfidenceValue("70%"),
            ensure_order=False,
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
                timeout=5,
                delay=FISHING_DELAY,
                threshold=ConfidenceValue("60%"),
                ensure_order=False,
            )
        except GameTimeoutError:
            logging.info("Small fish caught.")
            return

        # Fishing Loop
        check_book_at = 20
        click_strong_pull_at = 10
        count = 0
        thread = None
        while True:
            count += 1
            screenshot = self.get_screenshot()

            if count % click_strong_pull_at == 0:
                if not thread or not thread.is_alive():
                    # don't log this its clicking like 5 million times
                    self.tap(
                        STRONG_PULL,
                        blocking=False,
                        log=False,
                    )

            if count % check_book_at == 0:
                # TODO for quest fishing spot book does not exist,
                # Would have to check for dialogue buttons or the sun/moon time switch
                if self.game_find_template_match(
                    "fishing/book.png",
                    crop_regions=CropRegions(left=0.9, bottom=0.9),
                    screenshot=screenshot,
                    threshold=ConfidenceValue("70%"),
                ):
                    logging.info("Fishing done")
                    # TODO Not sure how to detect a catch or loss here.
                    # Might have to OCR the remaining attempts?
                    break

            if not thread or not thread.is_alive():
                cropped = Cropping.crop(
                    screenshot,
                    CropRegions(left=0.1, right=0.1, top="980px", bottom="740px"),
                )
                top, middle = _find_fishing_colors_fast(cropped.image)
                if top and middle and top > middle:
                    thread = self._handle_hold_for_distance(
                        btn=btn,
                        distance=(top - middle),
                        thread=thread,
                    )
            # Without this CPU usage will go insane
            sleep(FISHING_DELAY)
        return

    def _handle_hold_for_distance(
        self,
        btn: Coordinates,
        distance: int,
        thread: threading.Thread | None,
    ) -> threading.Thread | None:
        # TODO distance and duration could be adjusted
        # Holds are not blocking so processing can continue
        # Debug log disabled to reduce IO/Processing time
        if distance > DISTANCE_600:
            return self.hold(btn, duration=1.75, blocking=False, log=False)
        if distance > DISTANCE_400:
            return self.hold(btn, duration=1.25, blocking=False, log=False)
        if distance > DISTANCE_200:
            return self.hold(btn, duration=0.75, blocking=False, log=False)
        if distance > DISTANCE_100:
            return self.hold(btn, duration=0.5, blocking=False, log=False)
        if distance > DISTANCE_50:
            return self.hold(btn, duration=0.25, blocking=False, log=False)
        return thread

    def _passed_screenshot_delay_check(self) -> bool:
        start_time = time.time()
        _ = self.get_screenshot()
        total_time = (time.time() - start_time) * 1000
        if total_time > MAX_SCREENSHOT_DELAY_IN_MS:
            logging.error(
                f"Screenshot delay of {int(total_time)} ms is too high, "
                "fishing cannot work."
            )
            return False

        if total_time > MAX_SCREENSHOT_DELAY_IN_MS:
            logging.warning(
                f"Screenshot delay of {int(total_time)} ms might be too high, "
                "if you experiences issues please report them."
            )
        else:
            logging.info(f"Screenshot delay of {int(total_time)} ms")
        return True

    def _passed_input_delay_check(self) -> bool:
        total_time = 0.0
        iterations = 10
        for _ in range(iterations):
            start_time = time.time()
            self.tap(PointOutsideDisplay(), log=False)
            total_time += (time.time() - start_time) * 1000
        average_time = total_time / iterations
        if average_time > MAX_AVG_INPUT_DELAY_IN_MS:
            logging.error(
                f"Average Input delay of {int(average_time)} ms is too high, "
                "fishing cannot work."
            )
            return False

        if average_time > MAX_AVG_INPUT_DELAY_CANDIDATE:
            logging.warning(
                f"Average Input delay of {int(average_time)} ms might be too high, "
                "if you experiences issues please report them."
            )
        else:
            logging.info(f"Average Input delay of {int(average_time)} ms")
        return True


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
