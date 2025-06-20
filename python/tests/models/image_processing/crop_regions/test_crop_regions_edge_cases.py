from adb_auto_player.models.image_processing import CropRegions, CropValue


class TestCropRegionsEdgeCases:
    """Test CropRegions edge cases and boundary conditions."""

    def test_zero_values(self):
        """Test with zero values."""
        crop_regions = CropRegions(left=0, right=0.0, top="0px", bottom="0%")
        assert crop_regions.left.value == 0
        assert crop_regions.right.value == 0.0
        assert crop_regions.top.value == 0
        assert crop_regions.bottom.value == 0.0

    def test_maximum_valid_percentages(self):
        """Test with maximum valid percentage combinations."""
        # Maximum horizontal combination
        crop_regions = CropRegions(left=0.4, right=0.59)
        assert crop_regions.left.value == 0.4
        assert crop_regions.right.value == 0.59

        # Maximum vertical combination
        crop_regions = CropRegions(top=0.1, bottom=0.89)
        assert crop_regions.top.value == 0.1
        assert crop_regions.bottom.value == 0.89

    def test_single_side_high_percentage(self):
        """Test with single side having high percentage."""
        crop_regions = CropRegions(left=0.9, right=0.05)
        assert crop_regions.left.value == 0.9
        assert crop_regions.right.value == 0.05

        crop_regions = CropRegions(top=0.05, bottom=0.9)
        assert crop_regions.top.value == 0.05
        assert crop_regions.bottom.value == 0.9

    def test_very_small_percentages(self):
        """Test with very small percentage values."""
        crop_regions = CropRegions(left=0.001, right=0.002, top=0.003, bottom=0.004)
        assert crop_regions.left.value == 0.001
        assert crop_regions.right.value == 0.002
        assert crop_regions.top.value == 0.003
        assert crop_regions.bottom.value == 0.004

    def test_large_pixel_values(self):
        """Test with large pixel values."""
        crop_regions = CropRegions(left=9999, right=8888, top=7777, bottom=6666)
        assert crop_regions.left.value == 9999
        assert crop_regions.right.value == 8888
        assert crop_regions.top.value == 7777
        assert crop_regions.bottom.value == 6666

    def test_attributes_are_crop_values(self):
        """Test that all attributes are CropValue instances."""
        crop_regions = CropRegions(left=10, right=0.2, top="30px", bottom="40%")
        assert isinstance(crop_regions.left, CropValue)
        assert isinstance(crop_regions.right, CropValue)
        assert isinstance(crop_regions.top, CropValue)
        assert isinstance(crop_regions.bottom, CropValue)
