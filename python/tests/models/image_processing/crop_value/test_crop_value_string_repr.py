from adb_auto_player.models.image_processing import CropValue


class TestCropValueStringRepresentation:
    """Test CropValue string representations."""

    def test_str_pixels(self):
        """Test string representation for pixel values."""
        crop = CropValue(100)
        assert str(crop) == "100px"

    def test_str_percentage(self):
        """Test string representation for percentage values."""
        crop = CropValue(0.8)
        assert str(crop) == "80.0%"

        crop2 = CropValue(0.123)
        assert str(crop2) == "12.3%"

    def test_repr_pixels(self):
        """Test repr representation for pixel values."""
        crop = CropValue(100)
        assert repr(crop) == "CropValue(100)"

    def test_repr_percentage(self):
        """Test repr representation for percentage values."""
        crop = CropValue(0.8)
        assert repr(crop) == "CropValue(0.8)"
