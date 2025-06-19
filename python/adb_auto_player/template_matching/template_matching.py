"""ADB Auto Player Template Matching Module."""

from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np
from adb_auto_player.models.template_matching import MatchMode


class CropRegions(NamedTuple):
    """Crop named tuple."""

    left: float = 0  # Percentage to crop from the left side
    right: float = 0  # Percentage to crop from the right side
    top: float = 0  # Percentage to crop from the top side
    bottom: float = 0  # Percentage to crop from the bottom side


template_cache: dict[str, np.ndarray] = {}


def load_image(
    image_path: Path,
    image_scale_factor: float = 1.0,
    grayscale: bool = False,
) -> np.ndarray:
    """Loads an image from disk or returns the cached version if available.

    Resizes the image if needed and stores it in the global template_cache.

    Args:
        image_path: Path to the template image.
        image_scale_factor: Scale factor for resizing the image.
        grayscale: Whether to convert the image to grayscale.

    Returns:
        np.ndarray
    """
    if image_path.suffix == "":
        image_path = image_path.with_suffix(".png")

    cache_key = f"{image_path}_{image_scale_factor}_grayscale={grayscale}"
    if cache_key in template_cache:
        return template_cache[cache_key]

    image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Failed to load image from path: {image_path}")

    if image_scale_factor != 1.0:
        new_width = int(image.shape[1] * image_scale_factor)
        new_height = int(image.shape[0] * image_scale_factor)
        image = cv2.resize(
            image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4
        )

    if grayscale:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    template_cache[cache_key] = image
    return image


def crop_image(image: np.ndarray, crop: CropRegions) -> tuple[np.ndarray, int, int]:
    """Crop an image based on percentage values for each side.

    Args:
        image (np.ndarray): The input image to be cropped.
        crop (Crop): The crop percentage values for each edge.

    Returns:
        Cropped image.
        Number of pixels cropped from the left.
        Number of pixels cropped from the top.

    Raises:
        ValueError: If any crop percentage is negative,
            the sum of left and right crop percentages is 1.0 or greater
            or the sum of top and bottom crop percentages is 1.0 or greater.
    """
    if all(v == 0 for v in (crop.left, crop.right, crop.top, crop.bottom)):
        return image, 0, 0

    if any(v < 0 for v in (crop.left, crop.right, crop.top, crop.bottom)):
        raise ValueError("Crop percentages cannot be negative.")
    if crop.left + crop.right >= 1.0:
        raise ValueError("left + right must be less than 1.0.")
    if crop.top + crop.bottom >= 1.0:
        raise ValueError("top + bottom must be less than 1.0.")

    height, width = image.shape[:2]
    left_px = int(width * crop.left)
    right_px = int(width * (1 - crop.right))
    top_px = int(height * crop.top)
    bottom_px = int(height * (1 - crop.bottom))

    cropped_image = image[top_px:bottom_px, left_px:right_px]
    return cropped_image, left_px, top_px


def similar_image(
    base_image: np.ndarray,
    template_image: np.ndarray,
    threshold: float = 0.9,
    grayscale: bool = False,
) -> bool:
    """Compares the similarity between two images.

    Args:
        base_image: The reference image.
        template_image: The image to compare against.
        threshold: Minimum similarity threshold (0-1). If the similarity is below this,
          returns False.
        grayscale: Whether to convert both images to grayscale before comparison.

    Returns:
        True if the base_image matches the template_image based on the given threshold.
    """
    base_cv, template_cv = _prepare_images_for_processing(
        base_image=base_image,
        template_image=template_image,
        threshold=threshold,
        grayscale=grayscale,
    )

    result = cv2.matchTemplate(base_cv, template_cv, method=cv2.TM_CCOEFF_NORMED)
    return np.max(result) >= threshold


def find_template_match(
    base_image: np.ndarray,
    template_image: np.ndarray,
    match_mode: MatchMode = MatchMode.BEST,
    threshold: float = 0.9,
    grayscale: bool = False,
) -> tuple[int, int] | None:
    """Find a template image within a base image with different matching modes.

    Args:
        base_image: The image to search in
        template_image: The template to search for
        match_mode: The mode determining which match to return if multiple are found
        threshold: Minimum similarity threshold (0-1)
        grayscale: Whether to convert images to grayscale before matching

    Returns:
        tuple of (center_x, center_y) coordinates or None if no match found
    """
    base_cv, template_cv = _prepare_images_for_processing(
        base_image=base_image,
        template_image=template_image,
        threshold=threshold,
        grayscale=grayscale,
    )

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
    base_image: np.ndarray,
    template_image: np.ndarray,
    threshold: float = 0.9,
    grayscale: bool = False,
    min_distance: int = 10,
) -> list[tuple[int, int]]:
    """Find all matches.

    Args:
        base_image (np.ndarray): Base image.
        template_image (np.ndarray): Template image.
        threshold (float, optional): Image similarity threshold. Defaults to 0.9.
        grayscale (bool, optional): Convert to grayscale boolean. Defaults to False.
        min_distance (int, optional): Minimum distance between matches. Defaults to 10.

    Returns:
        list[tuple[int, int]]: List of found coordinates.
    """
    base_cv, template_cv = _prepare_images_for_processing(
        base_image=base_image,
        template_image=template_image,
        threshold=threshold,
        grayscale=grayscale,
    )

    result = cv2.matchTemplate(base_cv, template_cv, cv2.TM_CCOEFF_NORMED)
    match_locations = np.where(result >= threshold)

    template_height, template_width = template_cv.shape[:2]
    centers = []

    for x, y in zip(match_locations[1], match_locations[0]):
        center_x = x + template_width // 2
        center_y = y + template_height // 2
        centers.append((center_x, center_y))

    if centers:
        centers = _suppress_close_matches(centers, min_distance)

    return centers


def find_worst_template_match(
    base_image: np.ndarray,
    template_image: np.ndarray,
    grayscale: bool = False,
) -> tuple[int, int] | None:
    """Find the area in the base image that is most different from the template.

    This function creates a difference map between the template and all possible
    positions in the base image, then returns the position with the maximum difference.

    Args:
        base_image: The image to search in
        template_image: The template to compare against
        grayscale: Whether to convert images to grayscale before comparison

    Returns:
        tuple of (center_x, center_y) coordinates for the most different region
    """
    base_cv, template_cv = _prepare_images_for_processing(
        base_image=base_image, template_image=template_image, grayscale=grayscale
    )

    # Create a difference map using OpenCV's matchTemplate with TM_SQDIFF
    # TM_SQDIFF gives higher values for worse matches (sum of squared differences)
    diff_map = cv2.matchTemplate(base_cv, template_cv, cv2.TM_SQDIFF)

    # Find the location with the maximum difference (worst match)
    _, max_val, _, max_diff_loc = cv2.minMaxLoc(diff_map)
    min_difference_threshold = 10000
    if max_val < min_difference_threshold:
        return None
    max_diff_x, max_diff_y = max_diff_loc

    # Calculate center coordinates
    template_height, template_width = template_cv.shape[:2]
    center_x = max_diff_x + template_width // 2
    center_y = max_diff_y + template_height // 2

    return center_x, center_y


def _suppress_close_matches(
    matches: list[tuple[int, int]], min_distance: int
) -> list[tuple[int, int]]:
    """Suppresses closely spaced matches to return distinct results.

    Uses a simple clustering method based on minimum distance.
    """
    if not matches:
        return []

    matches_array = np.array(matches)
    suppressed: list[tuple[int, int]] = []  # type: ignore
    dimension = 2

    for match in matches_array:
        match_tuple = tuple(match)
        if len(match_tuple) == dimension and all(
            np.linalg.norm(match_tuple - np.array(s)) >= min_distance
            for s in suppressed
        ):
            suppressed.append(match_tuple)  # type: ignore
    return suppressed


def _validate_threshold(threshold: float) -> None:
    """Validate the threshold value.

    Raises:
        ValueError: If the threshold is less than 0 or greater than 1.
    """
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError(f"Threshold must be between 0 and 1, got {threshold}")


def _validate_template_size(base_image: np.ndarray, template_image: np.ndarray) -> None:
    """Validate that the template image is smaller than the base image.

    Args:
        base_image: The base Image as ndarray
        template_image: The template Image as ndarray

    Raises:
        ValueError: If the template is larger than the base image in any dimension
    """
    base_height, base_width = base_image.shape[:2]
    template_height, template_width = template_image.shape[:2]

    if template_height > base_height or template_width > base_width:
        cv2.imwrite("debug/validate_template_size_base_image.png", base_image)
        cv2.imwrite("debug/validate_template_size_template_image.png", template_image)
        raise ValueError(
            f"Template must be smaller than the base image. "
            f"Base size: ({base_width}, {base_height}), "
            f"Template size: ({template_width}, {template_height})"
        )


def _prepare_images_for_processing(
    base_image, template_image, threshold=None, grayscale=True
):
    """Validates inputs and prepares images for template matching.

    Args:
        base_image (np.ndarray): The base image.
        template_image (np.ndarray): The template image.
        threshold (float, optional): Matching threshold to validate.
        grayscale (bool): Whether to convert images to grayscale.

    Returns:
        Tuple[np.ndarray, np.ndarray]: Prepared base and template images.
    """
    if threshold is not None:
        _validate_threshold(threshold)

    _validate_template_size(base_image=base_image, template_image=template_image)

    if grayscale:
        return convert_to_grayscale(base_image), convert_to_grayscale(template_image)

    return base_image, template_image


_NUM_COLORS_IN_RGB = 3


def convert_to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert np.ndarray to grayscale."""
    if len(image.shape) == _NUM_COLORS_IN_RGB:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image
