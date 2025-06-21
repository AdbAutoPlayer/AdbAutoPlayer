from pathlib import Path

from adb_auto_player.image_manipulation import load_image
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.template_matching import similar_image


class TestSimilarImage:
    """Tests for similar_image function."""

    def test_identical_images_returns_true(self):
        """Test that identical images return True."""
        image1 = load_image(Path(__file__).parent / "data" / "guitar_girl_busk")
        result = similar_image(image1, image1, ConfidenceValue("80%"))

        assert result is True

    def test_different_images_returns_false(self):
        """Test that different images return False."""
        image1 = load_image(Path(__file__).parent / "data" / "guitar_girl_busk")
        image2 = load_image(Path(__file__).parent / "data" / "guitar_girl_play")

        result = similar_image(image1, image2, ConfidenceValue("90%"))

        assert result is False
