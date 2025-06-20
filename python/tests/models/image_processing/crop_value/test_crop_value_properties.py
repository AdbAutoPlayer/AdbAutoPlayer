import pytest
from adb_auto_player.models.image_processing import CropValue


class TestCropValueProperties:
    """Test CropValue properties and methods."""

    def test_is_pixels_property(self):
        """Test is_pixels property."""
        pixel_crop = CropValue(100)
        percentage_crop = CropValue(0.5)

        assert pixel_crop.is_pixels is True
        assert percentage_crop.is_pixels is False

    def test_percentage_property_success(self):
        """Test percentage property for percentage values."""
        crop = CropValue(0.8)
        assert crop.percentage == 0.8

    def test_percentage_property_error(self):
        """Test percentage property error for pixel values."""
        crop = CropValue(100)
        with pytest.raises(
            ValueError, match="Cannot convert pixel value to percentage"
        ):
            _ = crop.percentage

    def test_pixels_property_success(self):
        """Test pixels property for pixel values."""
        crop = CropValue(100)
        assert crop.pixels == 100

    def test_pixels_property_error(self):
        """Test pixels property error for percentage values."""
        crop = CropValue(0.8)
        with pytest.raises(
            ValueError, match="Cannot convert percentage value to pixels"
        ):
            _ = crop.pixels
