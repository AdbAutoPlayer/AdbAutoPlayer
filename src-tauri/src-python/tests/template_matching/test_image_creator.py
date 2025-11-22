import numpy as np


class TestImageCreator:
    """Helper class to create test images."""

    @staticmethod
    def create_solid_color_image(
        width: int, height: int, color: tuple[int, int, int] = (255, 255, 255)
    ) -> np.ndarray:
        """Create a solid color image."""
        return np.full((height, width, 3), color, dtype=np.uint8)

    @staticmethod
    def create_image_with_pattern(
        width: int,
        height: int,
        pattern_x: int,
        pattern_y: int,
        pattern_width: int,
        pattern_height: int,
        bg_color: tuple[int, int, int] = (0, 0, 0),
        pattern_color: tuple[int, int, int] = (255, 255, 255),
    ) -> np.ndarray:
        """Create an image with a rectangular pattern at specified location."""
        image = np.full((height, width, 3), bg_color, dtype=np.uint8)
        image[
            pattern_y : pattern_y + pattern_height,
            pattern_x : pattern_x + pattern_width,
        ] = pattern_color
        return image

    @staticmethod
    def create_gradient_image(width: int, height: int) -> np.ndarray:
        """Create a gradient image."""
        image = np.zeros((height, width, 3), dtype=np.uint8)
        for i in range(width):
            image[:, i] = [
                int(255 * i / width),
                int(255 * i / width),
                int(255 * i / width),
            ]
        return image
