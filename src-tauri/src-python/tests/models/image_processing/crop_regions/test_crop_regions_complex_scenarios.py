import pytest
from adb_auto_player.models.image_manipulation import CropRegions


class TestCropRegionsComplexScenarios:
    """Test complex scenarios and combinations."""

    def test_all_percentages_valid(self):
        """Test all percentage values that are valid."""
        crop_regions = CropRegions(left=0.1, right=0.2, top=0.15, bottom=0.25)
        assert crop_regions.left.value == 0.1
        assert crop_regions.right.value == 0.2
        assert crop_regions.top.value == 0.15
        assert crop_regions.bottom.value == 0.25

    def test_all_pixels_valid(self):
        """Test all pixel values."""
        crop_regions = CropRegions(left=50, right=100, top=75, bottom=125)
        assert crop_regions.left.value == 50
        assert crop_regions.right.value == 100
        assert crop_regions.top.value == 75
        assert crop_regions.bottom.value == 125

    def test_mixed_valid_combination(self):
        """Test mixed pixel and percentage combinations."""
        crop_regions = CropRegions(left="50px", right=0.3, top=100, bottom="25%")
        assert crop_regions.left.value == 50
        assert crop_regions.left.is_pixels is True
        assert crop_regions.right.value == 0.3
        assert crop_regions.right.is_pixels is False
        assert crop_regions.top.value == 100
        assert crop_regions.top.is_pixels is True
        assert crop_regions.bottom.value == 0.25
        assert crop_regions.bottom.is_pixels is False

    def test_boundary_percentage_validation(self):
        """Test boundary conditions for percentage validation."""
        # Just under the limit
        crop_regions = CropRegions(left=0.49, right=0.49)
        assert crop_regions.left.value == 0.49
        assert crop_regions.right.value == 0.49

        # Just at the limit (should fail)
        with pytest.raises(ValueError):
            CropRegions(left=0.5, right=0.5)

        # Just over the limit (should fail)
        with pytest.raises(ValueError):
            CropRegions(left=0.5000001, right=0.5)
