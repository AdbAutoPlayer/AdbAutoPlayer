"""Crop regions dataclass for image processing."""

from dataclasses import dataclass

from .crop_value import CropValue

_MAX_PERCENTAGE_EXCLUSIVE = 1.0


@dataclass
class CropRegions:
    """Represents crop regions for image processing with flexible input formats.

    Used to define what should be cropped from an image.

    Supports:
    - Percentage floats: 0.0-0.999... (0.0 to under 1.0)
    - Pixel integers: 0, 10, 100 (non-negative integers)
    - String formats: "0.8", "80%", "80 %", "80", "100px", "100 px"

    Validation:
    - No negative values allowed
    - Percentage values must be < 1.0 (100% would delete entire image)
    - left + right must be < 1.0 (for percentage values)
    - top + bottom must be < 1.0 (for percentage values)
    - Pixel values with decimals (e.g., "80.5px") are not allowed
    """

    left: CropValue
    right: CropValue
    top: CropValue
    bottom: CropValue

    def __init__(
        self,
        left: str | int | float = 0,
        right: str | int | float = 0,
        top: str | int | float = 0,
        bottom: str | int | float = 0,
    ):
        """Initialize crop regions from various input formats.

        Args:
            left: Left crop value
            right: Right crop value
            top: Top crop value
            bottom: Bottom crop value

        Raises:
            ValueError: If crop values are invalid or conflicting
        """
        self.left = CropValue(left)
        self.right = CropValue(right)
        self.top = CropValue(top)
        self.bottom = CropValue(bottom)

        # Validate that opposing sides don't crop the entire image
        self._validate_opposing_sides()

    def _validate_opposing_sides(self) -> None:
        """Validate that opposing crop values don't exceed 100% combined.

        Raises:
            ValueError: If left+right or top+bottom would crop entire image
        """
        # Only validate percentage values (pixel validation requires image dimensions)
        if not self.left.is_pixels and not self.right.is_pixels:
            if (self.left.value + self.right.value) >= _MAX_PERCENTAGE_EXCLUSIVE:
                raise ValueError(
                    f"Left({self.left.value * 100:.1f}%) + "
                    f"Right({self.right.value * 100:.1f}%) "
                    f"crops >= 100% of image width"
                )

        if not self.top.is_pixels and not self.bottom.is_pixels:
            if (self.top.value + self.bottom.value) >= _MAX_PERCENTAGE_EXCLUSIVE:
                raise ValueError(
                    f"Top({self.top.value * 100:.1f}%) + "
                    f"Bottom({self.bottom.value * 100:.1f}%) "
                    f"crops >= 100% of image height"
                )

    def __str__(self) -> str:
        """String representation."""
        return (
            f"CropRegions(left={self.left}, right={self.right}, top={self.top}, "
            f"bottom={self.bottom})"
        )

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return (
            f"CropRegions(left={self.left!r}, right={self.right!r}, "
            f"top={self.top!r}, bottom={self.bottom!r})"
        )
