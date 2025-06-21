from pathlib import Path

import numpy as np
from adb_auto_player.image_manipulation import load_image
from adb_auto_player.template_matching import find_worst_template_match

from .test_image_creator import TestImageCreator


class TestFindWorstTemplateMatch:
    """Tests for find_worst_template_match function."""

    def test_find_worst_match(self):
        """Test finding the worst template match."""
        # Create image with varied content
        base_image = TestImageCreator.create_gradient_image(200, 200)
        # Add a distinct pattern
        base_image[50:80, 50:80] = (255, 0, 0)  # Red square

        template = np.full((30, 30, 3), (0, 255, 0), dtype=np.uint8)  # Green template

        result = find_worst_template_match(base_image, template)

        assert result is not None
        assert result.box.width == 30
        assert result.box.height == 30

    def test_same_image_returns_none(self):
        image = load_image(Path(__file__).parent / "data" / "small_note")
        template = load_image(Path(__file__).parent / "data" / "small_note")
        result = find_worst_template_match(image, template)

        # Should return None if difference is below threshold
        assert result is None

    def test_grayscale_worst_match(self):
        """Test worst match with grayscale conversion."""
        base_image = TestImageCreator.create_image_with_pattern(
            200, 200, 50, 50, 30, 30, (255, 255, 255), (0, 0, 0)
        )
        template = np.full((30, 30, 3), (128, 128, 128), dtype=np.uint8)

        result = find_worst_template_match(base_image, template, grayscale=True)

        assert result is not None
