import io
from typing import Tuple, NoReturn

import cv2
import numpy as np
from PIL import Image
from adbutils._device import AdbDevice

import adb_auto_player.logger as logging


def get_screenshot(device: AdbDevice) -> Image.Image | NoReturn:
    screenshot_data = device.shell("screencap -p", encoding=None)
    if isinstance(screenshot_data, bytes):
        return Image.open(io.BytesIO(screenshot_data))

    logging.critical_and_exit(
        f"Screenshots cannot be recorded from device: {device.serial}"
    )


def __load_image(image_path: str) -> Image.Image | NoReturn:
    try:
        image = Image.open(image_path)
        image.load()
        return image
    except FileNotFoundError:
        logging.critical_and_exit(f"The file '{image_path}' does not exist")
    except IOError:
        logging.critical_and_exit(f"The file '{image_path}' is not a valid image")


def find_center(
    device: AdbDevice,
    template_image_path: str,
    threshold: float = 0.9,
    grayscale: bool = False,
) -> Tuple[int, int] | None:
    return __find_template_center(
        base_image=get_screenshot(device),
        template_image=__load_image(image_path=template_image_path),
        threshold=threshold,
        grayscale=grayscale,
    )


def __find_template_center(
    base_image: Image.Image,
    template_image: Image.Image,
    threshold: float = 0.9,
    grayscale: bool = False,
) -> Tuple[int, int] | None:
    base_cv = cv2.cvtColor(np.array(base_image), cv2.COLOR_RGB2BGR)
    template_cv = cv2.cvtColor(np.array(template_image), cv2.COLOR_RGB2BGR)

    if grayscale:
        base_cv = cv2.cvtColor(base_cv, cv2.COLOR_BGR2GRAY)
        template_cv = cv2.cvtColor(template_cv, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(base_cv, template_cv, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        template_height, template_width = template_cv.shape[:2]
        center_x = max_loc[0] + template_width // 2
        center_y = max_loc[1] + template_height // 2
        return center_x, center_y

    return None


def find_all_centers(
    device: AdbDevice,
    template_image_path: str,
    threshold: float = 0.9,
    grayscale: bool = False,
) -> list[Tuple[int, int]]:
    return __find_all_template_centers(
        base_image=get_screenshot(device),
        template_image=__load_image(image_path=template_image_path),
        threshold=threshold,
        grayscale=grayscale,
    )


def __find_all_template_centers(
    base_image: Image.Image,
    template_image: Image.Image,
    threshold: float = 0.9,
    grayscale: bool = False,
    min_distance: int = 10,  # min distance between results
) -> list[Tuple[int, int]]:
    base_cv = cv2.cvtColor(np.array(base_image), cv2.COLOR_RGB2BGR)
    template_cv = cv2.cvtColor(np.array(template_image), cv2.COLOR_RGB2BGR)

    if grayscale:
        base_cv = cv2.cvtColor(base_cv, cv2.COLOR_BGR2GRAY)
        template_cv = cv2.cvtColor(template_cv, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(base_cv, template_cv, cv2.TM_CCOEFF_NORMED)
    match_locations = np.where(result >= threshold)

    template_height, template_width = template_cv.shape[:2]
    centers = []

    for x, y in zip(match_locations[1], match_locations[0]):
        center_x = x + template_width // 2
        center_y = y + template_height // 2
        centers.append((center_x, center_y))

    if centers:
        centers = __suppress_close_matches(centers, min_distance)

    return centers


def __suppress_close_matches(
    matches: list[Tuple[int, int]], min_distance: int
) -> list[Tuple[int, int]]:
    """
    Suppresses closely spaced matches to return distinct results.
    Uses a simple clustering method based on minimum distance.
    """
    if not matches:
        return []

    matches_array = np.array(matches)
    suppressed: list[Tuple[int, int]] = []

    for match in matches_array:
        match_tuple = tuple(match)
        if len(match_tuple) == 2 and all(
            np.linalg.norm(match_tuple - np.array(s)) >= min_distance
            for s in suppressed
        ):
            suppressed.append(match_tuple)

    return suppressed
