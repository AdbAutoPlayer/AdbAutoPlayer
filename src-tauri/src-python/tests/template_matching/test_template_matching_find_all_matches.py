from pathlib import Path

import numpy as np
from adb_auto_player.image_manipulation import IO
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.template_matching import TemplateMatcher

from .test_image_creator import TestImageCreator


class TestFindAllTemplateMatches:
    """Tests for find_all_template_matches function."""

    def test_find_multiple_matches(self):
        """Test finding multiple template matches."""
        base_image = IO.load_image(
            Path(__file__).parent / "data" / "guitar_girl_with_notes"
        )
        template = IO.load_image(Path(__file__).parent / "data" / "small_note")

        results = TemplateMatcher.find_all_template_matches(
            base_image,
            template,
            ConfidenceValue("90%"),
        )
        assert len(results) == 4

        # Verify all matches have good confidence
        for result in results:
            assert result.confidence.value >= 0.8

    def test_no_matches_returns_empty_list(self):
        """Test that no matches returns empty list."""
        base_image = IO.load_image(
            Path(__file__).parent / "data" / "guitar_girl_no_notes"
        )
        template = IO.load_image(Path(__file__).parent / "data" / "small_note")

        results = TemplateMatcher.find_all_template_matches(
            base_image,
            template,
            ConfidenceValue("90%"),
        )

        assert results == []

    def test_grayscale_matching_multiple(self):
        """Test finding multiple matches with grayscale conversion."""
        base_image = TestImageCreator.create_solid_color_image(300, 300, (255, 0, 0))

        # Add patterns with different colors but same grayscale intensity
        base_image[50:80, 50:80] = (0, 255, 0)
        base_image[150:180, 150:180] = (0, 0, 255)

        template = np.full((30, 30, 3), (0, 255, 0), dtype=np.uint8)

        results = TemplateMatcher.find_all_template_matches(
            base_image,
            template,
            ConfidenceValue("80%"),
            grayscale=True,
            min_distance=50,
        )

        assert len(results) >= 1  # Should find at least one match in grayscale
