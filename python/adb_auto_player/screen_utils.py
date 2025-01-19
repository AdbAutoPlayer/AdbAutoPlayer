from enum import StrEnum, auto
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


class MatchMode(StrEnum):
    BEST = auto()
    TOP_LEFT = auto()
    TOP_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()
    LEFT_TOP = auto()
    LEFT_BOTTOM = auto()
    RIGHT_TOP = auto()
    RIGHT_BOTTOM = auto()


template_cache: dict[str, Image.Image] = {}


def load_image(image_path: Path, image_scale_factor: float = 1.0) -> Image.Image:
    """
    Loads an image from disk or returns the cached version if available.
    Resizes the image if needed and stores it in the global template_cache.

    :param image_path: Path to the template image.
    :param image_scale_factor: Scale factor for resizing the image.
    :return: PIL Image object.

    :raises FileNotFoundError:
    :raises IOError:
    """

    cache_key = f"{str(image_path)}_{image_scale_factor}"
    if cache_key in template_cache:
        return template_cache[cache_key]

    image = Image.open(image_path)
    image.load()

    if image_scale_factor != 1.0:
        new_width = int(image.width * image_scale_factor)
        new_height = int(image.height * image_scale_factor)
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    template_cache[cache_key] = image
    return image


def clear_template_cache() -> None:
    global template_cache
    template_cache.clear()


def find_template_match(
    base_image: Image.Image,
    template_image: Image.Image,
    match_mode: MatchMode = MatchMode.BEST,
    threshold: float = 0.9,
    grayscale: bool = False,
) -> tuple[int, int] | None:
    """
    Find a template image within a base image with different matching modes.

    Args:
        base_image: The image to search in
        template_image: The template to search for
        match_mode: The mode determining which match to return if multiple are found
        threshold: Minimum similarity threshold (0-1)
        grayscale: Whether to convert images to grayscale before matching

    Returns:
        tuple of (center_x, center_y) coordinates or None if no match found
    """
    base_cv = cv2.cvtColor(np.array(base_image), cv2.COLOR_RGB2BGR)
    template_cv = cv2.cvtColor(np.array(template_image), cv2.COLOR_RGB2BGR)

    if grayscale:
        base_cv = cv2.cvtColor(base_cv, cv2.COLOR_BGR2GRAY)
        template_cv = cv2.cvtColor(template_cv, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(base_cv, template_cv, cv2.TM_CCOEFF_NORMED)
    if match_mode == MatchMode.BEST:
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if max_val >= threshold:
            template_height, template_width = template_cv.shape[:2]
            center_x = max_loc[0] + template_width // 2
            center_y = max_loc[1] + template_height // 2
            return center_x, center_y
        return None

    match_locations = np.where(result >= threshold)
    if len(match_locations[0]) == 0:
        return None

    template_height, template_width = template_cv.shape[:2]
    matches = list(zip(match_locations[1], match_locations[0]))  # x, y coordinates

    key_functions = {
        MatchMode.TOP_LEFT: lambda loc: (loc[1], loc[0]),
        MatchMode.TOP_RIGHT: lambda loc: (loc[1], -loc[0]),
        MatchMode.BOTTOM_LEFT: lambda loc: (-loc[1], loc[0]),
        MatchMode.BOTTOM_RIGHT: lambda loc: (-loc[1], -loc[0]),
        MatchMode.LEFT_TOP: lambda loc: (loc[0], loc[1]),
        MatchMode.LEFT_BOTTOM: lambda loc: (loc[0], -loc[1]),
        MatchMode.RIGHT_TOP: lambda loc: (-loc[0], loc[1]),
        MatchMode.RIGHT_BOTTOM: lambda loc: (-loc[0], -loc[1]),
    }

    selected_match = min(matches, key=key_functions[match_mode])

    center_x = selected_match[0] + template_width // 2
    center_y = selected_match[1] + template_height // 2

    return center_x, center_y


def find_all_template_matches(
    base_image: Image.Image,
    template_image: Image.Image,
    threshold: float = 0.9,
    grayscale: bool = False,
    min_distance: int = 10,
) -> list[tuple[int, int]]:
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
    matches: list[tuple[int, int]], min_distance: int
) -> list[tuple[int, int]]:
    """
    Suppresses closely spaced matches to return distinct results.
    Uses a simple clustering method based on minimum distance.
    """
    if not matches:
        return []

    matches_array = np.array(matches)
    suppressed: list[tuple[int, int]] = []  # type: ignore

    for match in matches_array:
        match_tuple = tuple(match)
        if len(match_tuple) == 2 and all(
            np.linalg.norm(match_tuple - np.array(s)) >= min_distance
            for s in suppressed
        ):
            suppressed.append(match_tuple)  # type: ignore
    return suppressed
