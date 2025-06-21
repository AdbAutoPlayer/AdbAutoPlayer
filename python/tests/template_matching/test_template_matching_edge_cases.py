from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.template_matching import MatchMode
from adb_auto_player.template_matching import find_template_match

from .test_image_creator import TestImageCreator


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

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
