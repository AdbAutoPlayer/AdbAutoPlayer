"""Color processing utilities.

This module provides functions for color space conversions and other
color-related image processing tasks.
"""

import cv2
import numpy as np

_NUM_COLORS_IN_RGB = 3


def to_grayscale(image: np.ndarray) -> np.ndarray:
    """Convert a BGR color image to grayscale.

    Args:
        image (np.ndarray): Input image in BGR color format or already grayscale.

    Returns:
        np.ndarray: Grayscale image if input was color; otherwise,
            returns the input unchanged.
    """
    if len(image.shape) == _NUM_COLORS_IN_RGB:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return image
