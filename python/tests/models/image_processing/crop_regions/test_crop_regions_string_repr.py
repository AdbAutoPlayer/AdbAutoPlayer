from adb_auto_player.models.image_processing import CropRegions


class TestCropRegionsStringRepresentation:
    """Test CropRegions string representations."""

    def test_str_representation(self):
        """Test string representation."""
        crop_regions = CropRegions(left=10, right="20%", top=0.3, bottom="40px")
        expected = "CropRegions(left=10px, right=20.0%, top=30.0%, bottom=40px)"
        assert str(crop_regions) == expected

    def test_str_representation_defaults(self):
        """Test string representation with default values."""
        crop_regions = CropRegions()
        expected = "CropRegions(left=0px, right=0px, top=0px, bottom=0px)"
        assert str(crop_regions) == expected

    def test_repr_representation(self):
        """Test repr representation."""
        crop_regions = CropRegions(left=10, right="20%", top=0.3, bottom="40px")
        expected = (
            "CropRegions(left=CropValue(10), right=CropValue(0.2), "
            "top=CropValue(0.3), bottom=CropValue(40))"
        )
        assert repr(crop_regions) == expected
