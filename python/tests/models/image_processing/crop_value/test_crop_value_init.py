from adb_auto_player.models.image_manipulation import CropValue


class TestCropValueInit:
    """Test CropValue initialization with various input formats."""

    def test_int_pixels(self):
        """Test initialization with integer pixel values."""
        crop = CropValue(10)
        assert crop.value == 10
        assert crop.is_pixels is True

    def test_float_percentage(self):
        """Test initialization with float percentage values."""
        crop = CropValue(0.5)
        assert crop.value == 0.5
        assert crop.is_pixels is False

    def test_zero_values(self):
        """Test initialization with zero values."""
        crop_int = CropValue(0)
        assert crop_int.value == 0
        assert crop_int.is_pixels is True

        crop_float = CropValue(0.0)
        assert crop_float.value == 0.0
        assert crop_float.is_pixels is False

    def test_string_pixels(self):
        """Test initialization with string pixel values."""
        crop = CropValue("100px")
        assert crop.value == 100
        assert crop.is_pixels is True

    def test_string_pixels_with_spaces(self):
        """Test initialization with string pixel values containing spaces."""
        crop = CropValue("100 px")
        assert crop.value == 100
        assert crop.is_pixels is True

        crop2 = CropValue(" 100px ")
        assert crop2.value == 100
        assert crop2.is_pixels is True

    def test_string_percentage(self):
        """Test initialization with string percentage values."""
        crop = CropValue("80%")
        assert crop.value == 0.8
        assert crop.is_pixels is False

    def test_string_percentage_with_spaces(self):
        """Test initialization with string percentage values containing spaces."""
        crop = CropValue("80 %")
        assert crop.value == 0.8
        assert crop.is_pixels is False

        crop2 = CropValue(" 80% ")
        assert crop2.value == 0.8
        assert crop2.is_pixels is False

    def test_string_float_percentage(self):
        """Test initialization with string float values as percentages."""
        crop = CropValue("0.5")
        assert crop.value == 0.5
        assert crop.is_pixels is False

    def test_string_int_pixels(self):
        """Test initialization with string integer values as pixels."""
        crop = CropValue("100")
        assert crop.value == 100
        assert crop.is_pixels is True

    def test_edge_case_max_percentage(self):
        """Test initialization with maximum valid percentage."""
        crop = CropValue(0.999)
        assert crop.value == 0.999
        assert crop.is_pixels is False
