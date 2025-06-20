import pytest
from adb_auto_player.models.image_processing import CropRegions


class TestCropRegionsInvalidInputs:
    """Test CropRegions with invalid inputs."""

    def test_invalid_crop_value_formats(self):
        """Test that invalid CropValue formats raise appropriate errors."""
        with pytest.raises(ValueError):
            CropRegions(left="invalid")

        with pytest.raises(ValueError):
            CropRegions(right=-10)

        with pytest.raises(ValueError):
            CropRegions(top=1.5)

        with pytest.raises(ValueError):
            CropRegions(bottom="150%")

    def test_decimal_pixels_error(self):
        """Test that decimal pixel values raise errors."""
        with pytest.raises(ValueError, match="Pixel values cannot have decimals"):
            CropRegions(left="10.5px")

    def test_negative_values_error(self):
        """Test that negative values raise errors."""
        with pytest.raises(ValueError, match="cannot be negative"):
            CropRegions(left=-5)

        with pytest.raises(ValueError, match="cannot be negative"):
            CropRegions(right="-10%")

        with pytest.raises(ValueError, match="cannot be negative"):
            CropRegions(top=-0.1)

        with pytest.raises(ValueError, match="cannot be negative"):
            CropRegions(bottom="-5px")
