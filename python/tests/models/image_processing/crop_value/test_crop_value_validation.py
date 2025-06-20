import pytest
from adb_auto_player.models.image_processing import CropValue


class TestCropValueValidation:
    """Test CropValue validation and error handling."""

    def test_negative_int_error(self):
        """Test that negative integers raise ValueError."""
        with pytest.raises(ValueError, match="Pixel values cannot be negative"):
            CropValue(-10)

    def test_negative_float_error(self):
        """Test that negative floats raise ValueError."""
        with pytest.raises(ValueError, match="Percentage values cannot be negative"):
            CropValue(-0.1)

    def test_percentage_too_large_error(self):
        """Test that percentage >= 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Percentage values must be < 1.0"):
            CropValue(1.0)

        with pytest.raises(ValueError, match="Percentage values must be < 1.0"):
            CropValue(1.5)

    def test_string_negative_pixels_error(self):
        """Test that negative string pixels raise ValueError."""
        with pytest.raises(ValueError, match="Pixel values cannot be negative"):
            CropValue("-10px")

    def test_string_negative_percentage_error(self):
        """Test that negative string percentages raise ValueError."""
        with pytest.raises(ValueError, match="Percentage values cannot be negative"):
            CropValue("-10%")

        with pytest.raises(ValueError, match="Percentage values cannot be negative"):
            CropValue("-0.1")

    def test_string_percentage_too_large_error(self):
        """Test that string percentages >= 100% raise ValueError."""
        with pytest.raises(ValueError, match="Percentage values must be < 100%"):
            CropValue("100%")

        with pytest.raises(ValueError, match="Percentage values must be < 100%"):
            CropValue("150%")

    def test_string_float_too_large_error(self):
        """Test that string floats >= 1.0 raise ValueError."""
        with pytest.raises(ValueError, match="Percentage values must be < 1.0"):
            CropValue("1.0")

        with pytest.raises(ValueError, match="Percentage values must be < 1.0"):
            CropValue("1.5")

    def test_decimal_pixels_error(self):
        """Test that decimal pixel values raise ValueError."""
        with pytest.raises(ValueError, match="Pixel values cannot have decimals"):
            CropValue("80.5px")

    def test_invalid_string_format_error(self):
        """Test that invalid string formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid crop value format"):
            CropValue("abc")

        with pytest.raises(ValueError, match="Invalid pixel format"):
            CropValue("abcpx")

        with pytest.raises(ValueError, match="Invalid percentage format"):
            CropValue("abc%")

    def test_unsupported_type_error(self):
        """Test that unsupported types raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported crop value type"):
            CropValue([1, 2, 3])

        with pytest.raises(ValueError, match="Unsupported crop value type"):
            CropValue({"value": 10})
