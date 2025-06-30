import pytest
from adb_auto_player.template_matching.template_matcher import (
    _prepare_images_for_processing,
)

from .test_image_creator import TestImageCreator


class TestPrepareImagesForProcessing:
    """Tests for _prepare_images_for_processing function."""

    def test_grayscale_conversion_enabled(self):
        """Test that images are converted to grayscale when enabled."""
        base_image = TestImageCreator.create_solid_color_image(100, 100, (255, 0, 0))
        template_image = TestImageCreator.create_solid_color_image(50, 50, (0, 255, 0))

        base_result, template_result = _prepare_images_for_processing(
            base_image, template_image, grayscale=True
        )

        # Grayscale images should have 2 dimensions
        assert len(base_result.shape) == 2
        assert len(template_result.shape) == 2

    def test_grayscale_conversion_disabled(self):
        """Test that images remain color when grayscale is disabled."""
        base_image = TestImageCreator.create_solid_color_image(100, 100, (255, 0, 0))
        template_image = TestImageCreator.create_solid_color_image(50, 50, (0, 255, 0))

        base_result, template_result = _prepare_images_for_processing(
            base_image, template_image, grayscale=False
        )

        # Color images should maintain their original dimensions
        assert base_result.shape == base_image.shape
        assert template_result.shape == template_image.shape

    def test_validation_called(self):
        """Test that template size validation is performed."""
        base_image = TestImageCreator.create_solid_color_image(50, 50)
        template_image = TestImageCreator.create_solid_color_image(100, 100)

        with pytest.raises(
            ValueError, match="Template must be smaller than the base image"
        ):
            _prepare_images_for_processing(base_image, template_image)
