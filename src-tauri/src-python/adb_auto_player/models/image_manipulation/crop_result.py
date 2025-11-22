"""Module for handling image cropping results.

Defines the CropResult data class which stores the cropped image and its offset
relative to the original image.
"""

from dataclasses import dataclass

import numpy as np

from ..geometry import Point


@dataclass(frozen=True)
class CropResult:
    """Represents the result of cropping an image.

    Attributes:
        image (np.ndarray): The cropped image as a NumPy array.
        offset (Point): The top-left point offset of the cropped image relative
            to the original.
    """

    image: np.ndarray
    offset: Point
