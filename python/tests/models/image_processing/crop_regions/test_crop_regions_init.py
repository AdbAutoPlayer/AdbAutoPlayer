from adb_auto_player.models.image_processing import CropRegions


class TestCropRegionsInit:
    """Test CropRegions initialization with various input formats."""

    def test_default_init(self):
        """Test initialization with default values."""
        crop_regions = CropRegions()
        assert crop_regions.left.value == 0
        assert crop_regions.right.value == 0
        assert crop_regions.top.value == 0
        assert crop_regions.bottom.value == 0
        assert crop_regions.left.is_pixels is True
        assert crop_regions.right.is_pixels is True
        assert crop_regions.top.is_pixels is True
        assert crop_regions.bottom.is_pixels is True

    def test_init_with_integers(self):
        """Test initialization with integer pixel values."""
        crop_regions = CropRegions(left=10, right=20, top=30, bottom=40)
        assert crop_regions.left.value == 10
        assert crop_regions.right.value == 20
        assert crop_regions.top.value == 30
        assert crop_regions.bottom.value == 40
        assert all(
            region.is_pixels
            for region in [
                crop_regions.left,
                crop_regions.right,
                crop_regions.top,
                crop_regions.bottom,
            ]
        )

    def test_init_with_floats(self):
        """Test initialization with float percentage values."""
        crop_regions = CropRegions(left=0.1, right=0.2, top=0.3, bottom=0.4)
        assert crop_regions.left.value == 0.1
        assert crop_regions.right.value == 0.2
        assert crop_regions.top.value == 0.3
        assert crop_regions.bottom.value == 0.4
        assert all(
            not region.is_pixels
            for region in [
                crop_regions.left,
                crop_regions.right,
                crop_regions.top,
                crop_regions.bottom,
            ]
        )

    def test_init_with_strings(self):
        """Test initialization with string values."""
        crop_regions = CropRegions(left="10px", right="20%", top="30", bottom="0.4")
        assert crop_regions.left.value == 10
        assert crop_regions.right.value == 0.2
        assert crop_regions.top.value == 30
        assert crop_regions.bottom.value == 0.4
        assert crop_regions.left.is_pixels is True
        assert crop_regions.right.is_pixels is False
        assert crop_regions.top.is_pixels is True
        assert crop_regions.bottom.is_pixels is False

    def test_init_mixed_formats(self):
        """Test initialization with mixed input formats."""
        crop_regions = CropRegions(left=10, right="20%", top=0.3, bottom="40px")
        assert crop_regions.left.value == 10
        assert crop_regions.right.value == 0.2
        assert crop_regions.top.value == 0.3
        assert crop_regions.bottom.value == 40
        assert crop_regions.left.is_pixels is True
        assert crop_regions.right.is_pixels is False
        assert crop_regions.top.is_pixels is False
        assert crop_regions.bottom.is_pixels is True

    def test_init_partial_values(self):
        """Test initialization with only some values specified."""
        crop_regions = CropRegions(left=10, top=0.2)
        assert crop_regions.left.value == 10
        assert crop_regions.right.value == 0
        assert crop_regions.top.value == 0.2
        assert crop_regions.bottom.value == 0
        assert crop_regions.left.is_pixels is True
        assert crop_regions.right.is_pixels is True
        assert crop_regions.top.is_pixels is False
        assert crop_regions.bottom.is_pixels is True
