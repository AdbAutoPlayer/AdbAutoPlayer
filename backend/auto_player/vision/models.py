"""Models for vision."""

from enum import StrEnum, auto
from typing import NamedTuple, Generic, TypeVar

T = TypeVar("T")


class MatchMode(StrEnum):
    """Match mode for template matching."""

    BEST = auto()
    TOP_LEFT = auto()
    TOP_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()
    LEFT_TOP = auto()
    LEFT_BOTTOM = auto()
    RIGHT_TOP = auto()
    RIGHT_BOTTOM = auto()


class Crop(NamedTuple):
    """Percentages of the image to crop from each edge.

    Values are floats from 0.0 to 1.0, representing the percentage
    of the image dimension to crop from that edge.
    """

    top: float = 0.0
    bottom: float = 0.0
    left: float = 0.0
    right: float = 0.0


class Preprocessing(NamedTuple):
    """Image preprocessing options.

    Attributes:
        grayscale: Whether to convert the image to grayscale.
        crop: A Crop object defining how the image should be cropped
              before further processing or matching. This crop is
              typically applied to a template image.
        scale_factor: Scaling factor for resizing the image.
    """

    grayscale: bool
    crop: Crop
    scale_factor: float = 1.0


class Image(NamedTuple, Generic[T]):
    """Represents an image, potentially with associated preprocessing.

    Attributes:
        image: The raw image data itself (e.g., a NumPy array for OpenCV).
        preprocessing: Optional Preprocessing directives that have been
                       applied or should be applied to this image.
    """

    image: T
    preprocessing: Preprocessing | None = None


class VisionWait(NamedTuple):
    """Specifies waiting conditions for vision operations.

    Attributes:
        appears: Time in milliseconds to wait for an image to appear.
                 If 0, no waiting for appearance.
        disappears: Time in milliseconds to wait for an image to disappear.
                    If 0, no waiting for disappearance.
    """

    appears: int = 0
    disappears: int = 0
