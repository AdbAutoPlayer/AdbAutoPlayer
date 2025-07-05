"""This module provides functionality to crop image."""

import numpy as np
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions, CropResult, CropValue


class Cropping:
    """Cropping related operations."""

    @staticmethod
    def crop(image: np.ndarray, crop_regions: CropRegions) -> CropResult:
        """Crop an image based on the specified crop regions.

        Args:
            image: The input image to be cropped as a numpy array
            crop_regions: CropRegions object specifying how much to crop from each side

        Returns:
            CropResult containing the cropped image and offset information

        Raises:
            ValueError: If crop regions would result in invalid cropping or
                if pixel values exceed image dimensions
        """
        # Check for no-op case
        if all(
            cv.value == 0
            for cv in [
                crop_regions.left,
                crop_regions.right,
                crop_regions.top,
                crop_regions.bottom,
            ]
        ):
            return CropResult(image=image, offset=Point(x=0, y=0))

        if image.size == 0:
            raise ValueError("Cannot crop empty image")

        height, width = image.shape[:2]

        # Convert crop values to pixels
        left_px = _crop_value_to_pixels(crop_regions.left, width, "left", width)
        right_px = _crop_value_to_pixels(crop_regions.right, width, "right", width)
        top_px = _crop_value_to_pixels(crop_regions.top, height, "top", height)
        bottom_px = _crop_value_to_pixels(crop_regions.bottom, height, "bottom", height)

        # Validate pixel crop values don't exceed image dimensions
        _validate_pixel_crops(
            horizontal_crops=(left_px, right_px),
            vertical_crops=(top_px, bottom_px),
            dimensions=(width, height),
        )

        # Calculate crop boundaries
        left_boundary = left_px
        right_boundary = width - right_px
        top_boundary = top_px
        bottom_boundary = height - bottom_px

        # Validate boundaries make sense
        if left_boundary >= right_boundary:
            raise ValueError(
                f"Left crop ({left_px}px) + Right crop ({right_px}px) "
                f"would crop entire image width ({width}px)"
            )
        if top_boundary >= bottom_boundary:
            raise ValueError(
                f"Top crop ({top_px}px) + Bottom crop ({bottom_px}px) "
                f"would crop entire image height ({height}px)"
            )

        # Perform the crop
        cropped_image = image[
            top_boundary:bottom_boundary, left_boundary:right_boundary
        ]

        return CropResult(
            image=cropped_image, offset=Point(x=left_boundary, y=top_boundary)
        )


def _crop_value_to_pixels(
    crop_value: CropValue, dimension: int, side_name: str, total_dimension: int
) -> int:
    """Convert a CropValue to pixels.

    Args:
        crop_value: The CropValue to convert
        dimension: The dimension (width or height) to calculate against
        side_name: Name of the side for error messages
        total_dimension: Total dimension for validation

    Returns:
        Number of pixels to crop

    Raises:
        ValueError: If pixel value exceeds dimension
    """
    if crop_value.is_pixels:
        pixels = crop_value.pixels
        if pixels > total_dimension:
            raise ValueError(
                f"{side_name.capitalize()} crop ({pixels}px) exceeds "
                f"image dimension ({total_dimension}px)"
            )
        return pixels
    else:
        return int(dimension * crop_value.percentage)


def _validate_pixel_crops(
    horizontal_crops: tuple[int, int],
    vertical_crops: tuple[int, int],
    dimensions: tuple[int, int],
) -> None:
    """Validate that pixel crop values don't exceed image dimensions.

    Args:
        horizontal_crops: Tuple of (left_px, right_px)
        vertical_crops: Tuple of (top_px, bottom_px)
        dimensions: Tuple of (width, height)

    Raises:
        ValueError: If crop values would crop entire image
    """
    left_px, right_px = horizontal_crops
    top_px, bottom_px = vertical_crops
    width, height = dimensions

    if left_px + right_px >= width:
        raise ValueError(
            f"Left crop ({left_px}px) + Right crop ({right_px}px) "
            f"would crop entire image width ({width}px)"
        )

    if top_px + bottom_px >= height:
        raise ValueError(
            f"Top crop ({top_px}px) + Bottom crop ({bottom_px}px) "
            f"would crop entire image height ({height}px)"
        )
