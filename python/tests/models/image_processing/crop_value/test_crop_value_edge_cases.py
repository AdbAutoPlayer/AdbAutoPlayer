"""Unit tests for CropValue class."""

import pytest
from adb_auto_player.models.image_processing import CropValue


class TestCropValueEdgeCases:
    """Test CropValue edge cases and boundary conditions."""

    def test_very_small_percentage(self):
        """Test very small percentage values."""
        crop = CropValue(0.001)
        assert crop.value == 0.001
        assert crop.is_pixels is False

    def test_large_pixel_values(self):
        """Test large pixel values."""
        crop = CropValue(9999)
        assert crop.value == 9999
        assert crop.is_pixels is True

    def test_string_zero_percentage(self):
        """Test string zero percentage."""
        crop = CropValue("0%")
        assert crop.value == 0.0
        assert crop.is_pixels is False

    def test_string_zero_pixels(self):
        """Test string zero pixels."""
        crop = CropValue("0px")
        assert crop.value == 0
        assert crop.is_pixels is True

    def test_boundary_percentage_values(self):
        """Test boundary percentage values."""
        # Just under 1.0
        crop = CropValue(0.9999)
        assert crop.value == 0.9999
        assert crop.is_pixels is False

        # Just under 100%
        crop2 = CropValue("99.9%")
        assert crop2.value == pytest.approx(0.999)
        assert crop2.is_pixels is False
