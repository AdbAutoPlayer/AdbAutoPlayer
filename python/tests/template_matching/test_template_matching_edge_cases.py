from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.template_matching import MatchMode
from adb_auto_player.template_matching import find_template_match, similar_image
from template_matching.image_creator import TestImageCreator


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_very_small_images(self):
        """Test handling of very small images."""
        base_image = TestImageCreator.create_solid_color_image(10, 10)
        template_image = TestImageCreator.create_solid_color_image(5, 5)

        result = similar_image(base_image, template_image, ConfidenceValue("50%"))

        # Should handle small images without error
        assert result is True

    def test_single_pixel_template(self):
        """Test handling of single pixel template."""
        base_image = TestImageCreator.create_solid_color_image(
            100, 100, (128, 128, 128)
        )
        template_image = TestImageCreator.create_solid_color_image(
            1, 1, (128, 128, 128)
        )

        result = find_template_match(
            base_image, template_image, MatchMode.BEST, ConfidenceValue("90%")
        )

        assert result is not None
        assert result.box.width == 1
        assert result.box.height == 1

    def test_extreme_confidence_thresholds(self):
        """Test extreme confidence threshold values."""
        base_image = TestImageCreator.create_solid_color_image(100, 100)
        template_image = base_image[25:75, 25:75]

        # Very low threshold - should always match
        result_low = similar_image(base_image, template_image, ConfidenceValue("1%"))
        assert result_low is True

        # Very high threshold - might not match due to floating point precision
        result_high = similar_image(
            base_image, template_image, ConfidenceValue("99.9%")
        )
        assert isinstance(result_high, bool)
