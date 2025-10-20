"""ADB Auto Player Template Matching Module."""

import logging

import cv2
import numpy as np
from adb_auto_player.image_manipulation import Color
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.template_matching import MatchMode, MatchResult


class TemplateMatcher:
    """A collection of static methods for template matching operations."""

    @staticmethod
    def similar_image(
        base_image: np.ndarray,
        template_image: np.ndarray,
        threshold: ConfidenceValue = ConfidenceValue("90%"),
        grayscale: bool = False,
    ) -> bool:
        """Compares the similarity between two images.

        Args:
            base_image: The reference image.
            template_image: The image to compare against.
            threshold: Minimum similarity threshold (0-1). Below this, returns False.
            grayscale: Whether to convert both images to grayscale before comparison.

        Returns:
            True if the base_image matches the template_image.
        """
        base_cv, template_cv = _prepare_images_for_processing(
            base_image=base_image,
            template_image=template_image,
            grayscale=grayscale,
        )

        result = TemplateMatcher._match_template(
            base_cv, template_cv, method=cv2.TM_CCOEFF_NORMED
        )
        return bool(np.max(result) >= threshold.cv2_format)

    @staticmethod
    def _match_template(
        image: cv2.typing.MatLike,
        templ: cv2.typing.MatLike,
        method: int,
    ) -> cv2.typing.MatLike:
        try:
            return cv2.matchTemplate(
                image=image,
                templ=templ,
                method=method,
            )
        except cv2.error as e:
            logging.error(
                "CV2 Error detected please send cv2error_base.png and "
                "cv2error_template.png from the debug dir to Yules for investigation"
            )
            cv2.imwrite("debug/cv2error_base.png", image)
            cv2.imwrite("debug/cv2error_template.png", templ)
            raise e

    @staticmethod
    def find_template_match(
        base_image: np.ndarray,
        template_image: np.ndarray,
        match_mode: MatchMode = MatchMode.BEST,
        threshold: ConfidenceValue = ConfidenceValue("90%"),
        grayscale: bool = False,
    ) -> MatchResult | None:
        """Find a template image within a base image with different matching modes.

        Args:
            base_image: The image to search in
            template_image: The template to search for
            match_mode: The mode determining which match to return if multiple are found
            threshold: Minimum similarity threshold (0-1)
            grayscale: Whether to convert images to grayscale before matching

        Returns:
            MatchResult or None if no match found
        """
        base_cv, template_cv = _prepare_images_for_processing(
            base_image=base_image,
            template_image=template_image,
            grayscale=grayscale,
        )

        template_height, template_width = template_cv.shape[:2]

        result = TemplateMatcher._match_template(
            base_cv, template_cv, cv2.TM_CCOEFF_NORMED
        )
        if match_mode == MatchMode.BEST:
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val >= threshold.cv2_format:
                return MatchResult(
                    box=Box(
                        top_left=Point(x=max_loc[0], y=max_loc[1]),
                        width=template_width,
                        height=template_height,
                    ),
                    confidence=ConfidenceValue(max_val),
                )
            return None

        match_locations = np.where(result >= threshold.cv2_format)
        if len(match_locations[0]) == 0:
            return None

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
        confidence = result[selected_match[1], selected_match[0]]

        return MatchResult(
            box=Box(
                top_left=Point(x=selected_match[0], y=selected_match[1]),
                width=template_width,
                height=template_height,
            ),
            confidence=ConfidenceValue(float(confidence)),
        )

    @staticmethod
    def find_all_template_matches(
        base_image: np.ndarray,
        template_image: np.ndarray,
        threshold: ConfidenceValue = ConfidenceValue("90%"),
        grayscale: bool = False,
        min_distance: int = 10,
    ) -> list[MatchResult]:
        """Find all matches.

        Args:
            base_image (np.ndarray): Base image.
            template_image (np.ndarray): Template image.
            threshold (float, optional): Image similarity threshold. Default 0.9.
            grayscale (bool, optional): Convert to grayscale boolean. Default  False.
            min_distance (int, optional): Minimum distance between matches. Default 10.

        Returns:
            list[MatchResult]: List of matched boxes with confidence value.
        """
        base_cv, template_cv = _prepare_images_for_processing(
            base_image=base_image,
            template_image=template_image,
            grayscale=grayscale,
        )

        template_height, template_width = template_cv.shape[:2]

        result = TemplateMatcher._match_template(
            base_cv, template_cv, cv2.TM_CCOEFF_NORMED
        )
        match_locations = np.where(result >= threshold.cv2_format)

        top_left_points_with_scores = [
            ((x, y), result[y, x])
            for x, y in zip(match_locations[1], match_locations[0])
        ]

        if top_left_points_with_scores:
            top_left_points_with_scores.sort(key=lambda x: x[1], reverse=True)
            points = [pt for pt, _ in top_left_points_with_scores]
            filtered_points = _suppress_close_matches(points, min_distance)

            # Create a dict for quick confidence lookup
            score_lookup = {
                (x, y): score for (x, y), score in top_left_points_with_scores
            }
            return [
                MatchResult(
                    box=Box(
                        top_left=Point(x=pt[0], y=pt[1]),
                        width=template_width,
                        height=template_height,
                    ),
                    confidence=ConfidenceValue(float(score_lookup[pt])),
                )
                for pt in filtered_points
            ]
        else:
            return []

    @staticmethod
    def find_worst_template_match(
        base_image: np.ndarray,
        template_image: np.ndarray,
        grayscale: bool = False,
    ) -> MatchResult | None:
        """Find the area in the base image that is most different from the template.

        This function creates a difference map between the template and all possible
        positions in the base image, returns the position with the maximum difference.

        Args:
            base_image: The image to search in
            template_image: The template to compare against
            grayscale: Whether to convert images to grayscale before comparison

        Returns:
            MatchResult | None if no match was found.
        """
        base_cv, template_cv = _prepare_images_for_processing(
            base_image=base_image, template_image=template_image, grayscale=grayscale
        )

        # Create a difference map using OpenCV's matchTemplate with TM_SQDIFF
        # TM_SQDIFF gives higher values for worse matches (sum of squared differences)
        diff_map = TemplateMatcher._match_template(base_cv, template_cv, cv2.TM_SQDIFF)

        # Find the location with the maximum difference (worst match)
        _, max_val, _, max_diff_loc = cv2.minMaxLoc(diff_map)
        min_difference_threshold = 10000
        if max_val < min_difference_threshold:
            return None
        max_diff_x, max_diff_y = max_diff_loc

        template_height, template_width = template_cv.shape[:2]

        return MatchResult(
            box=Box(
                Point(x=max_diff_x, y=max_diff_y),
                width=template_width,
                height=template_height,
            ),
            confidence=ConfidenceValue(False),  # We don't have a confidence for this
        )


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
    base_image, template_image, grayscale=True
) -> tuple[np.ndarray, np.ndarray]:
    """Validates inputs and prepares images for template matching.

    Args:
        base_image (np.ndarray): The base image.
        template_image (np.ndarray): The template image.
        grayscale (bool): Whether to convert images to grayscale.

    Returns:
        Tuple[np.ndarray, np.ndarray]: Prepared base and template images.
    """
    _validate_template_size(base_image=base_image, template_image=template_image)

    if grayscale:
        return Color.to_grayscale(base_image), Color.to_grayscale(template_image)

    return base_image, template_image
