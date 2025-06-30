from pathlib import Path

import numpy as np
from adb_auto_player.image_manipulation import IO
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.template_matching import MatchMode
from adb_auto_player.template_matching import TemplateMatcher

from .test_image_creator import TestImageCreator


class TestFindTemplateMatch:
    """Tests for find_template_match function."""

    def test_perfect_match_found(self):
        """Test finding a perfect template match."""
        base_image = IO.load_image(
            Path(__file__).parent / "data" / "guitar_girl_with_notes"
        )
        template = IO.load_image(Path(__file__).parent / "data" / "small_note")

        result = TemplateMatcher.find_template_match(
            base_image, template, MatchMode.BEST, ConfidenceValue("100%")
        )

        assert result is not None

    def test_no_match_found_returns_none(self):
        """Test that no match returns None."""
        base_image = IO.load_image(
            Path(__file__).parent / "data" / "guitar_girl_no_notes"
        )
        template = IO.load_image(Path(__file__).parent / "data" / "small_note")

        result = TemplateMatcher.find_template_match(
            base_image, template, threshold=ConfidenceValue("40%")
        )

        assert result is None

    def test_different_match_modes(self):
        """Test different match modes return different results."""
        # Create image with multiple identical patterns
        base_image = TestImageCreator.create_solid_color_image(200, 200, (0, 0, 0))
        # Add patterns at different locations
        base_image[10:40, 10:40] = (255, 255, 255)  # Top-left
        base_image[10:40, 160:190] = (255, 255, 255)  # Top-right
        base_image[160:190, 10:40] = (255, 255, 255)  # Bottom-left
        base_image[160:190, 160:190] = (255, 255, 255)  # Bottom-right

        template = np.full((30, 30, 3), (255, 255, 255), dtype=np.uint8)

        # Test different modes
        top_left_result = TemplateMatcher.find_template_match(
            base_image, template, MatchMode.TOP_LEFT, ConfidenceValue("80%")
        )
        top_right_result = TemplateMatcher.find_template_match(
            base_image, template, MatchMode.TOP_RIGHT, ConfidenceValue("80%")
        )
        bottom_left_result = TemplateMatcher.find_template_match(
            base_image, template, MatchMode.BOTTOM_LEFT, ConfidenceValue("80%")
        )
        bottom_right_result = TemplateMatcher.find_template_match(
            base_image, template, MatchMode.BOTTOM_RIGHT, ConfidenceValue("80%")
        )

        assert top_left_result is not None
        assert top_right_result is not None
        assert bottom_left_result is not None
        assert bottom_right_result is not None

        # Verify different positions are returned
        positions = [
            (top_left_result.box.top_left.x, top_left_result.box.top_left.y),
            (top_right_result.box.top_left.x, top_right_result.box.top_left.y),
            (bottom_left_result.box.top_left.x, bottom_left_result.box.top_left.y),
            (bottom_right_result.box.top_left.x, bottom_right_result.box.top_left.y),
        ]

        # All positions should be different
        assert len(set(positions)) == 4

    def test_grayscale_matching(self):
        """Test template matching with grayscale conversion."""
        base_image = IO.load_image(
            Path(__file__).parent / "data" / "guitar_girl_with_notes"
        )
        template = IO.load_image(Path(__file__).parent / "data" / "small_note")

        result = TemplateMatcher.find_template_match(
            base_image, template, threshold=ConfidenceValue("90%"), grayscale=True
        )

        assert result is not None
