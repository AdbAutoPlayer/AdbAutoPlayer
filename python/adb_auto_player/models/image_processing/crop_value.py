"""Crop Value."""

import re
from dataclasses import dataclass

_MIN_PERCENTAGE = 0.0
_MAX_PERCENTAGE_VALUE = 100.0
_MAX_PERCENTAGE_EXCLUSIVE = 1.0
_MIN_PIXELS = 0


@dataclass
class CropValue:
    """Represents a single crop value with flexible input formats.

    Supports:
    - Percentage floats: 0.0-0.999... (0.0 to under 1.0)
    - Pixel integers: 0, 10, 100 (non-negative integers)
    - String percentages: "0.8", "80%", "80 %"
    - String pixels: "80", "100px", "100 px"

    Note: 1.0 (100%) is not allowed as it would delete the entire image.
    Negative values are not allowed.
    """

    value: float | int

    def __init__(self, crop_value: str | int | float):
        """Initialize crop value from various input formats.

        Args:
            crop_value: Crop value in various formats

        Raises:
            ValueError: If crop value format is invalid or out of range
        """
        self.value = _parse_crop_value(crop_value)

    @property
    def is_pixels(self) -> bool:
        """Check if value represents pixels.

        Returns:
            True if value is pixels, False if percentage
        """
        return isinstance(self.value, int)

    @property
    def percentage(self) -> float:
        """Get value as percentage (only valid if not pixels).

        Returns:
            Value as percentage (0.0-0.999...)

        Raises:
            ValueError: If value is in pixels
        """
        if self.is_pixels:
            raise ValueError(
                "Cannot convert pixel value to percentage without image dimensions"
            )
        return self.value

    @property
    def pixels(self) -> int:
        """Get value as pixels (only valid if is pixels).

        Returns:
            Value as pixels

        Raises:
            ValueError: If value is percentage
        """
        if not self.is_pixels:
            raise ValueError(
                "Cannot convert percentage value to pixels without image dimensions"
            )
        return int(self.value)  # cast to make mypy happy.

    def __str__(self) -> str:
        """String representation."""
        if self.is_pixels:
            return f"{self.value}px"
        else:
            return f"{self.value * 100:.1f}%"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"CropValue({self.value})"


def _validate_pixel_value(value: int, original: str | int | float) -> int:
    if value < _MIN_PIXELS:
        raise ValueError(f"Pixel values cannot be negative: {original}")
    return value


def _validate_percentage_value(value: float, original: str | int | float) -> float:
    if value < _MIN_PERCENTAGE:
        raise ValueError(f"Percentage values cannot be negative: {original}")
    if value >= _MAX_PERCENTAGE_EXCLUSIVE:
        raise ValueError(f"Percentage values must be < 1.0: {original}")
    return value


def _parse_pixel_string(pixel_str: str) -> int:
    if "." in pixel_str:
        raise ValueError(f"Pixel values cannot have decimals: {pixel_str}px")
    try:
        pixel_value = int(pixel_str)
    except ValueError:
        raise ValueError(f"Invalid pixel format: {pixel_str}px")
    return _validate_pixel_value(pixel_value, pixel_str + "px")


def _parse_percentage_string(percent_str: str) -> float:
    try:
        percent_value = float(percent_str)
    except ValueError:
        raise ValueError(f"Invalid percentage format: {percent_str}%")
    if percent_value < 0:
        raise ValueError(f"Percentage values cannot be negative: {percent_str}%")
    if percent_value >= _MAX_PERCENTAGE_VALUE:
        raise ValueError(f"Percentage values must be < 100%: {percent_str}%")
    return percent_value / 100.0


def _parse_numeric_string(value_str: str) -> float | int:
    if "." in value_str:
        float_value = float(value_str)
        return _validate_percentage_value(float_value, value_str)
    else:
        int_value = int(value_str)
        return _validate_pixel_value(int_value, value_str)


def _parse_crop_value(crop_value: str | int | float) -> float | int:
    if isinstance(crop_value, str):
        crop_value = crop_value.strip()

        if crop_value.endswith("px"):
            return _parse_pixel_string(crop_value[:-2].strip())

        if crop_value.endswith("%"):
            return _parse_percentage_string(crop_value[:-1].strip())

        if not _is_valid_numeric_string(crop_value):
            raise ValueError(f"Invalid crop value format: {crop_value}")

        return _parse_numeric_string(crop_value)

    elif isinstance(crop_value, int):
        return _validate_pixel_value(crop_value, crop_value)

    elif isinstance(crop_value, float):
        return _validate_percentage_value(crop_value, crop_value)

    else:
        raise ValueError(f"Unsupported crop value type: {type(crop_value)}")


def _is_valid_numeric_string(s: str) -> bool:
    # Regex to match integer or float without trailing garbage
    # ^ start, $ end, \d+ one or more digits, (\.\d+)? optional decimal part
    # This lets negative value pass they will be validated later.
    pattern = r"^-?\d+(\.\d+)?$"
    return re.match(pattern, s) is not None
