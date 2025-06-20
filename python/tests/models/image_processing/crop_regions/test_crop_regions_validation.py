import pytest
from adb_auto_player.models.image_processing import CropRegions


class TestCropRegionsValidation:
    """Test CropRegions validation logic."""

    def test_valid_percentage_combinations(self):
        """Test valid percentage combinations that don't exceed 100%."""
        # Valid horizontal combination
        crop_regions = CropRegions(left=0.3, right=0.4)
        assert crop_regions.left.value == 0.3
        assert crop_regions.right.value == 0.4

        # Valid vertical combination
        crop_regions = CropRegions(top=0.2, bottom=0.5)
        assert crop_regions.top.value == 0.2
        assert crop_regions.bottom.value == 0.5

        # Maximum valid combination (just under 100%)
        crop_regions = CropRegions(left=0.4, right=0.59)
        assert crop_regions.left.value == 0.4
        assert crop_regions.right.value == 0.59

    def test_invalid_horizontal_percentage_combination(self):
        """Test that left + right >= 100% raises ValueError."""
        with pytest.raises(
            ValueError, match="Left.* Right.* crops >= 100% of image width"
        ):
            CropRegions(left=0.5, right=0.5)

        with pytest.raises(
            ValueError, match="Left.* Right.* crops >= 100% of image width"
        ):
            CropRegions(left=0.6, right=0.7)

        with pytest.raises(
            ValueError, match="Left.* Right.* crops >= 100% of image width"
        ):
            CropRegions(left="50%", right="50%")

    def test_invalid_vertical_percentage_combination(self):
        """Test that top + bottom >= 100% raises ValueError."""
        with pytest.raises(
            ValueError, match="Top.* Bottom.* crops >= 100% of image height"
        ):
            CropRegions(top=0.5, bottom=0.5)

        with pytest.raises(
            ValueError, match="Top.* Bottom.* crops >= 100% of image height"
        ):
            CropRegions(top=0.7, bottom=0.4)

        with pytest.raises(
            ValueError, match="Top.* Bottom.* crops >= 100% of image height"
        ):
            CropRegions(top="60%", bottom="40%")

    def test_mixed_pixels_and_percentages_no_validation(self):
        """Test that mixed pixels and percentages don't trigger validation."""
        # These should not raise errors as validation only applies to percentage pairs
        crop_regions = CropRegions(left=100, right=0.9)  # pixels + percentage
        assert crop_regions.left.value == 100
        assert crop_regions.right.value == 0.9

        crop_regions = CropRegions(top="50px", bottom="90%")  # pixels + percentage
        assert crop_regions.top.value == 50
        assert crop_regions.bottom.value == 0.9

    def test_pixels_only_no_validation(self):
        """Test that pixel-only values don't trigger validation."""
        # Large pixel values should not raise errors
        crop_regions = CropRegions(left=1000, right=2000, top=500, bottom=1500)
        assert crop_regions.left.value == 1000
        assert crop_regions.right.value == 2000
        assert crop_regions.top.value == 500
        assert crop_regions.bottom.value == 1500

    def test_edge_case_exactly_100_percent(self):
        """Test edge case where values exactly equal 100%."""
        with pytest.raises(ValueError, match="crops >= 100% of image width"):
            CropRegions(left=0.4, right=0.6)  # Exactly 100%

        with pytest.raises(ValueError, match="crops >= 100% of image height"):
            CropRegions(top=0.3, bottom=0.7)  # Exactly 100%
