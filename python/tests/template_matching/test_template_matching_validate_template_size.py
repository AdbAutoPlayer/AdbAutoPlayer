import pytest
from adb_auto_player.template_matching.template_matching import _validate_template_size

from .test_image_creator import TestImageCreator


class TestValidateTemplateSize:
    """Tests for _validate_template_size function."""

    def test_valid_template_size_passes(self):
        """Test that valid template size passes without error."""
        base_image = TestImageCreator.create_solid_color_image(200, 200)
        template_image = TestImageCreator.create_solid_color_image(100, 100)

        # Should not raise any exception
        _validate_template_size(base_image, template_image)

    def test_template_larger_width_raises_error(self):
        """Test that template larger in width raises ValueError."""
        base_image = TestImageCreator.create_solid_color_image(100, 200)
        template_image = TestImageCreator.create_solid_color_image(150, 100)

        with pytest.raises(
            ValueError, match="Template must be smaller than the base image"
        ):
            _validate_template_size(base_image, template_image)

    def test_template_larger_height_raises_error(self):
        """Test that template larger in height raises ValueError."""
        base_image = TestImageCreator.create_solid_color_image(200, 100)
        template_image = TestImageCreator.create_solid_color_image(100, 150)

        with pytest.raises(
            ValueError, match="Template must be smaller than the base image"
        ):
            _validate_template_size(base_image, template_image)

    def test_template_equal_size_passes(self):
        """Test that template equal in size passes."""
        base_image = TestImageCreator.create_solid_color_image(100, 100)
        template_image = TestImageCreator.create_solid_color_image(100, 100)

        # Should not raise any exception
        _validate_template_size(base_image, template_image)
