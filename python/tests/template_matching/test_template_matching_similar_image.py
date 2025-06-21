from pathlib import Path

from adb_auto_player.image_manipulation import load_image
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.template_matching import similar_image

from .test_image_creator import TestImageCreator


class TestSimilarImage:
    """Tests for similar_image function."""

    def test_identical_images_returns_true(self):
        """Test that identical images return True."""
        image = TestImageCreator.create_solid_color_image(100, 100, (128, 128, 128))

        result = similar_image(image, image, ConfidenceValue("90%"))

        assert result is True

    def test_different_images_returns_false(self):
        """Test that different images return False."""
        image1 = load_image(Path(__file__).parent / "data" / "guitar_girl_busk")
        image2 = load_image(Path(__file__).parent / "data" / "guitar_girl_play")

        result = similar_image(image1, image2, ConfidenceValue("90%"))

        assert result is False

    def test_similar_images_with_low_threshold_returns_true(self):
        """Test that slightly different images pass with low threshold."""
        image1 = TestImageCreator.create_solid_color_image(100, 100, (128, 128, 128))
        image2 = TestImageCreator.create_solid_color_image(100, 100, (130, 130, 130))

        result = similar_image(image1, image2, ConfidenceValue("10%"))

        assert result is True
