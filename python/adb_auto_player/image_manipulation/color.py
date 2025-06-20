"""Color processing utilities.

This module provides functions for color space conversions and other
color-related image processing tasks.
"""

from enum import StrEnum

import cv2
import numpy as np

_NUM_COLORS_IN_RGB = 3
_GRAYSCALE_DIMS = 2


class ColorFormat(StrEnum):
    """Enumeration for specifying the color format of an image.

    Attributes:
        BGR (str): Indicates the image color format is Blue-Green-Red channel order.
        RGB (str): Indicates the image color format is Red-Green-Blue channel order.
    """

    BGR = "BGR"
    RGB = "RGB"


def is_grayscale(image: np.ndarray) -> bool:
    """Check if an image is grayscale.

    An image is considered grayscale if it has only two dimensions,
    i.e., shape (height, width), without a channel dimension.

    Args:
        image (np.ndarray): Input image array.

    Returns:
        bool: True if the image is grayscale, False otherwise.
    """
    return len(image.shape) == _GRAYSCALE_DIMS


def to_grayscale(
    image: np.ndarray, color_format: ColorFormat = ColorFormat.BGR
) -> np.ndarray:
    """Convert a color image (BGR or RGB) to grayscale.

    If the input image is already grayscale, it returns the image unchanged.

    Args:
        image (np.ndarray): Input image in BGR or RGB format, or grayscale.
        color_format (ColorFormat): Enum specifying the color format of the input image.
            Defaults to ColorFormat.BGR.

    Raises:
        ValueError: If the input image is not grayscale or a 3-channel color image,
            or if the color_format is unsupported.

    Returns:
        np.ndarray: Grayscale image.
    """
    if is_grayscale(image):
        return image

    if not (
        len(image.shape) == _NUM_COLORS_IN_RGB and image.shape[2] == _NUM_COLORS_IN_RGB
    ):
        raise ValueError("Input image must have 3 channels (color image)")

    if color_format == ColorFormat.BGR:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif color_format == ColorFormat.RGB:
        return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    else:
        raise ValueError("Unsupported color format")


def to_rgb(image: np.ndarray) -> np.ndarray:
    """Convert a BGR image to RGB format.

    Args:
        image (np.ndarray): Input image in BGR color format.

    Returns:
        np.ndarray: Image converted to RGB format.

    Raises:
        ValueError: If the input image does not have 3 color channels.
    """
    if image.ndim != _NUM_COLORS_IN_RGB or image.shape[2] != _NUM_COLORS_IN_RGB:
        raise ValueError(
            f"Input image must have 3 color channels, got shape {image.shape}"
        )
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def to_bgr(image: np.ndarray) -> np.ndarray:
    """Convert an RGB image to BGR format.

    Args:
        image (np.ndarray): Input image in RGB color format.

    Returns:
        np.ndarray: Image converted to BGR format.

    Raises:
        ValueError: If the input image does not have 3 color channels.
    """
    if image.ndim != _NUM_COLORS_IN_RGB or image.shape[2] != _NUM_COLORS_IN_RGB:
        raise ValueError(
            f"Input image must have 3 color channels, got shape {image.shape}"
        )
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
