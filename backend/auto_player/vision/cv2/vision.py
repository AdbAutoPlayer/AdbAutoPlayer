import cv2
import numpy as np
import logging

from ..base import Vision
from ..models import (
    Image,
    Crop,
    Preprocessing,
    MatchMode,
)
from ...interaction.models import Coordinates

logger = logging.getLogger(__name__)

DEFAULT_CONFIDENCE = 0.8
RETRY_INTERVAL_SECONDS = 0.5


class Cv2Vision(Vision[np.ndarray]):
    """Concrete Vision implementation using OpenCV.

    Note: Connection-related aspects like direct screen capture are being decoupled.
    This service will expect image data (np.ndarray) for operations.
    """

    def __init__(
        self,
        default_confidence: float = DEFAULT_CONFIDENCE,
    ):
        """Initializes Cv2Vision.

        Args:
            default_confidence: Default confidence threshold for template matching.
        """
        self.default_confidence = default_confidence
        self._template_cache: dict[str, np.ndarray] = {}

    def _apply_preprocessing(
        self, image_data: np.ndarray, pp_options: Preprocessing
    ) -> tuple[np.ndarray, Coordinates]:
        """Applies preprocessing (crop, scaling, grayscale) to an image.

        Returns:
            A tuple containing the processed image data (np.ndarray)
            and the crop offset (Coordinates) relative to the original image.
        """
        crop_offset = Coordinates(x=0, y=0)
        if pp_options is None:
            return image_data.copy(), crop_offset

        processed_image_data = image_data.copy()

        if pp_options.crop and pp_options.crop != Crop():
            cropped_data, offset = self.crop_image_data(processed_image_data, pp_options.crop)
            processed_image_data = cropped_data
            crop_offset = offset  # Store the actual offset from cropping
            logger.debug(f"Applied crop. New dims: {processed_image_data.shape[:2]}, Offset: {crop_offset}")

        if pp_options.scale_factor != 1.0 and pp_options.scale_factor > 0:
            logger.debug(f"Applying scale factor: {pp_options.scale_factor}")
            new_width = int(processed_image_data.shape[1] * pp_options.scale_factor)
            new_height = int(processed_image_data.shape[0] * pp_options.scale_factor)
            if new_width > 0 and new_height > 0:
                processed_image_data = cv2.resize(
                    processed_image_data, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4
                )
                logger.debug(f"Applied scaling. New dims: {processed_image_data.shape[:2]}")
            else:
                logger.warning(
                    f"Skipping scaling for {pp_options.scale_factor} as it would result in zero or negative image dimensions."
                )
        elif pp_options.scale_factor <= 0:
            logger.warning(
                f"Invalid scale_factor: {pp_options.scale_factor}. Must be positive. Skipping scaling."
            )

        if pp_options.grayscale:
            if len(processed_image_data.shape) == 3 and processed_image_data.shape[2] == 3:
                processed_image_data = cv2.cvtColor(processed_image_data, cv2.COLOR_BGR2GRAY)
            elif len(processed_image_data.shape) == 3 and processed_image_data.shape[2] == 4:
                processed_image_data = cv2.cvtColor(processed_image_data, cv2.COLOR_BGRA2GRAY)
            elif len(processed_image_data.shape) == 2:
                pass
            else:
                logger.warning(
                    f"Cannot convert to grayscale, unsupported image shape: {processed_image_data.shape}."
                )
            logger.debug("Applied grayscale conversion (if applicable).")

        return processed_image_data, crop_offset

    def locate(
        self,
        input_screen_obj: Image[np.ndarray],
        target_template_obj: Image[np.ndarray],
        match_mode: MatchMode = MatchMode.BEST,
        confidence: float | None = None,
    ) -> Coordinates | None:
        """Locates a target template on the screen."""
        conf_to_use = confidence if confidence is not None else self.default_confidence
        self._validate_confidence(conf_to_use)

        template_pp = target_template_obj.preprocessing if target_template_obj.preprocessing is not None \
                      else Preprocessing(grayscale=False, crop=Crop(), scale_factor=1.0)
        processed_template_np, _ = self._apply_preprocessing(
            target_template_obj.image, template_pp
        )
        if processed_template_np is None or processed_template_np.size == 0:
            logger.error("Template image is empty after preprocessing.")
            return None

        screen_pp = input_screen_obj.preprocessing if input_screen_obj.preprocessing is not None \
                    else Preprocessing(grayscale=False, crop=Crop(), scale_factor=1.0)
        current_screen_np, screen_crop_offset = self._apply_preprocessing(
            input_screen_obj.image, screen_pp
        )
        if current_screen_np is None or current_screen_np.size == 0:
             logger.error("Input screen image is empty after preprocessing.")
             return None

        if not self._validate_template_size(current_screen_np, processed_template_np, raise_exception=False):
            return None

        match_coords_relative = self._find_match(
            current_screen_np,
            processed_template_np,
            conf_to_use,
            match_mode
        )

        if match_coords_relative:
            final_coords = Coordinates(
                x=match_coords_relative.x + screen_crop_offset.x,
                y=match_coords_relative.y + screen_crop_offset.y
            )
            logger.info(f"Template found at {final_coords} (mode: {match_mode}, conf: {conf_to_use:.2f}).")
            return final_coords
        else:
            logger.debug(f"Template not found (mode: {match_mode}, conf: {conf_to_use:.2f}).")
            return None

    def _find_match(
        self,
        screen_np: np.ndarray,
        template_np: np.ndarray,
        confidence: float,
        match_mode: MatchMode,
    ) -> Coordinates | None:
        """
        Helper to find a template match based on the specified mode.
        Assumes images are preprocessed (e.g., grayscale, scaled) as needed before this call.
        Assumes template size is validated against screen size before this call.
        """
        result = cv2.matchTemplate(screen_np, template_np, cv2.TM_CCOEFF_NORMED)
        template_height, template_width = template_np.shape[:2]

        if match_mode == MatchMode.BEST:
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val >= confidence:
                center_x = max_loc[0] + template_width // 2
                center_y = max_loc[1] + template_height // 2
                return Coordinates(x=center_x, y=center_y)
            return None
        else:
            match_locations_y, match_locations_x = np.where(result >= confidence)

            if len(match_locations_x) == 0:
                return None

            matches_top_left = list(zip(match_locations_x, match_locations_y))

            key_functions = {
                MatchMode.TOP_LEFT:     lambda loc: (loc[1], loc[0]),
                MatchMode.TOP_RIGHT:    lambda loc: (loc[1], -loc[0]),
                MatchMode.BOTTOM_LEFT:  lambda loc: (-loc[1], loc[0]),
                MatchMode.BOTTOM_RIGHT: lambda loc: (-loc[1], -loc[0]),
                MatchMode.LEFT_TOP:     lambda loc: (loc[0], loc[1]),
                MatchMode.LEFT_BOTTOM:  lambda loc: (loc[0], -loc[1]),
                MatchMode.RIGHT_TOP:    lambda loc: (-loc[0], loc[1]),
                MatchMode.RIGHT_BOTTOM: lambda loc: (-loc[0], -loc[1]),
            }

            if match_mode not in key_functions:
                logger.error(f"Unsupported MatchMode for specific location: {match_mode}. This should not happen.")
                _, max_val, _, max_loc = cv2.minMaxLoc(result)
                if max_val >= confidence:
                    center_x = max_loc[0] + template_width // 2
                    center_y = max_loc[1] + template_height // 2
                    return Coordinates(x=center_x, y=center_y)
                return None

            selected_match_top_left = min(matches_top_left, key=key_functions[match_mode])

            center_x = selected_match_top_left[0] + template_width // 2
            center_y = selected_match_top_left[1] + template_height // 2
            return Coordinates(x=center_x, y=center_y)

    def locate_all(
        self,
        input_screen_obj: Image[np.ndarray],
        target_template_obj: Image[np.ndarray],
        min_distance: int = 10,
        confidence: float | None = None,
    ) -> list[Coordinates] | None:
        """Locates all occurrences of a target template on the screen."""
        conf_to_use = confidence if confidence is not None else self.default_confidence
        self._validate_confidence(conf_to_use)

        template_pp = target_template_obj.preprocessing if target_template_obj.preprocessing is not None \
                      else Preprocessing(grayscale=False, crop=Crop(), scale_factor=1.0)
        processed_template_np, _ = self._apply_preprocessing(
            target_template_obj.image, template_pp
        )
        if processed_template_np is None or processed_template_np.size == 0:
            logger.error("Template image is empty after preprocessing for locate_all.")
            return None

        screen_pp = input_screen_obj.preprocessing if input_screen_obj.preprocessing is not None \
                    else Preprocessing(grayscale=False, crop=Crop(), scale_factor=1.0)
        current_screen_np, screen_crop_offset = self._apply_preprocessing(
            input_screen_obj.image, screen_pp
        )
        if current_screen_np is None or current_screen_np.size == 0:
            logger.error("Input screen image is empty after preprocessing for locate_all.")
            return None

        if not self._validate_template_size(current_screen_np, processed_template_np, raise_exception=False):
            return None

        found_matches_relative = self._find_all_matches(current_screen_np, processed_template_np, conf_to_use, min_distance)

        if not found_matches_relative:
            logger.debug("No matches found by _find_all_matches.")
            return None

        # Adjust coordinates by the screen crop offset
        adjusted_matches = [
            Coordinates(
                x=match.x + screen_crop_offset.x,
                y=match.y + screen_crop_offset.y
            ) for match in found_matches_relative
        ]

        logger.info(f"Located {len(adjusted_matches)} instances with confidence {conf_to_use:.2f} and min_distance {min_distance}.")
        return adjusted_matches

    def _find_all_matches(
        self,
        screen_np: np.ndarray,
        template_np: np.ndarray,
        confidence: float,
        min_distance: int
    ) -> list[Coordinates] | None:
        """
        Helper to find all template matches above a confidence, suppressing close ones.
        Assumes images are preprocessed and template size validated.
        """
        result = cv2.matchTemplate(screen_np, template_np, cv2.TM_CCOEFF_NORMED)
        match_locations_y, match_locations_x = np.where(result >= confidence)

        if len(match_locations_x) == 0:
            return None

        template_height, template_width = template_np.shape[:2]
        centers: list[Coordinates] = []
        for y, x in zip(match_locations_y, match_locations_x):
            center_x = x + template_width // 2
            center_y = y + template_height // 2
            centers.append(Coordinates(x=center_x, y=center_y))

        if not centers:
            return None

        suppressed_centers = self._suppress_close_coordinates(centers, min_distance)
        return suppressed_centers if suppressed_centers else None

    @staticmethod
    def _suppress_close_coordinates(coords: list[Coordinates], min_distance: int) -> list[Coordinates]:
        """Suppresses closely spaced coordinates."""
        if not coords:
            return []

        suppressed: list[Coordinates] = []
        for current_coord in coords:
            is_close_to_existing = False
            for sup_coord in suppressed:
                dist = np.sqrt(
                    (float(current_coord.x) - float(sup_coord.x))**2 +
                    (float(current_coord.y) - float(sup_coord.y))**2
                )
                if dist < min_distance:
                    is_close_to_existing = True
                    break
            if not is_close_to_existing:
                suppressed.append(current_coord)
        return suppressed

    def locate_worst_match(
        self,
        input_screen_obj: Image[np.ndarray],
        target_template_obj: Image[np.ndarray]
    ) -> Coordinates | None:
        """Finds the area in the input screen that is most different from the template."""
        template_pp = target_template_obj.preprocessing if target_template_obj.preprocessing is not None \
                      else Preprocessing(grayscale=False, crop=Crop(), scale_factor=1.0)
        processed_template_np, _ = self._apply_preprocessing(
            target_template_obj.image, template_pp
        )
        if processed_template_np is None or processed_template_np.size == 0:
            logger.error("Template image is empty after preprocessing for locate_worst_match.")
            return None

        screen_pp = input_screen_obj.preprocessing if input_screen_obj.preprocessing is not None \
                    else Preprocessing(grayscale=False, crop=Crop(), scale_factor=1.0)
        current_screen_np, screen_crop_offset = self._apply_preprocessing(
            input_screen_obj.image, screen_pp
        )
        if current_screen_np is None or current_screen_np.size == 0:
            logger.error("Input screen image is empty after preprocessing for locate_worst_match.")
            return None

        if not self._validate_template_size(current_screen_np, processed_template_np, raise_exception=False):
            logger.warning("Template size validation failed for locate_worst_match.")
            return None

        diff_map = cv2.matchTemplate(current_screen_np, processed_template_np, cv2.TM_SQDIFF)

        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(diff_map)

        MIN_DIFFERENCE_THRESHOLD_SQDIFF = 10000.0

        if max_val < MIN_DIFFERENCE_THRESHOLD_SQDIFF:
            logger.debug(
                f"Worst match found (value: {max_val:.2f}) is below threshold "
                f"({MIN_DIFFERENCE_THRESHOLD_SQDIFF:.2f}). No significant worst match."
            )
            return None

        worst_match_loc_x, worst_match_loc_y = max_loc

        template_height, template_width = processed_template_np.shape[:2]
        center_x_relative = worst_match_loc_x + template_width // 2
        center_y_relative = worst_match_loc_y + template_height // 2

        final_coords = Coordinates(
            x=center_x_relative + screen_crop_offset.x,
            y=center_y_relative + screen_crop_offset.y
        )

        logger.info(f"Worst match (most different area) found at {final_coords} with difference value {max_val:.2f}.")
        return final_coords

    def crop_image_data(
        self, image_data: np.ndarray, crop_settings: Crop
    ) -> tuple[np.ndarray, Coordinates]:
        """Crops the raw image data based on percentage Crop settings."""
        if not isinstance(image_data, np.ndarray):
            raise TypeError("image_data must be a numpy array.")
        if not isinstance(crop_settings, Crop):
            raise TypeError("crop_settings must be a Crop object.")

        if any(v < 0.0 for v in crop_settings):
            raise ValueError("Crop percentages cannot be negative.")
        if crop_settings.left + crop_settings.right > 1.0:
            raise ValueError("Sum of left and right crop percentages must be <= 1.0.")
        if crop_settings.top + crop_settings.bottom > 1.0:
            raise ValueError("Sum of top and bottom crop percentages must be <= 1.0.")

        original_height, original_width = image_data.shape[:2]

        crop_x_start = int(original_width * crop_settings.left)
        crop_x_end = original_width - int(original_width * crop_settings.right)
        crop_y_start = int(original_height * crop_settings.top)
        crop_y_end = original_height - int(original_height * crop_settings.bottom)

        if not (0 <= crop_y_start <= original_height and
                0 <= crop_y_end <= original_height and
                crop_y_start < crop_y_end and
                0 <= crop_x_start <= original_width and
                0 <= crop_x_end <= original_width and
                crop_x_start < crop_x_end):
            logger.error(
                f"Invalid crop pixel values calculated: "
                f"y:[{crop_y_start}:{crop_y_end}], x:[{crop_x_start}:{crop_x_end}] "
                f"from settings {crop_settings} for image size {original_width}x{original_height}."
            )
            raise ValueError(
                f"Calculated crop dimensions [{crop_x_start}:{crop_x_end}, {crop_y_start}:{crop_y_end}] are invalid for image size {original_width}x{original_height}."
            )

        cropped_image_data = image_data[crop_y_start:crop_y_end, crop_x_start:crop_x_end]

        crop_offset = Coordinates(x=crop_x_start, y=crop_y_start)
        logger.debug(
            f"Cropped image from {original_width}x{original_height} to "
            f"{cropped_image_data.shape[1]}x{cropped_image_data.shape[0]} "
            f"with offset {crop_offset} using settings {crop_settings}."
        )
        return cropped_image_data, crop_offset

    @staticmethod
    def _validate_confidence(confidence: float) -> None:
        """Validate the confidence value."""
        if not (0.0 <= confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {confidence}")

    @staticmethod
    def _validate_template_size(base_image: np.ndarray, template_image: np.ndarray, raise_exception: bool = True) -> bool:
        """Validate that the template image is not larger than the base image."""
        base_height, base_width = base_image.shape[:2]
        template_height, template_width = template_image.shape[:2]

        if template_height > base_height or template_width > base_width:
            msg = (
                f"Template must be smaller than or equal to the base image. "
                f"Base size: ({base_width}, {base_height}), "
                f"Template size: ({template_width}, {template_height})"
            )
            if raise_exception:
                logger.error(msg)
                raise ValueError(msg)
            else:
                logger.warning(msg)
                return False
        return True
