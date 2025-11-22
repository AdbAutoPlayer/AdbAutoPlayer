import numpy as np
import pytest
from adb_auto_player.image_manipulation import Cropping
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions, CropResult


class TestImageGeneration:
    """Helper methods for generating test images."""

    @staticmethod
    def create_test_image(
        width: int = 100, height: int = 100, channels: int = 3
    ) -> np.ndarray:
        """Create a synthetic test image with distinguishable patterns.

        Args:
            width: Image width
            height: Image height
            channels: Number of channels (1 for grayscale, 3 for RGB)

        Returns:
            Synthetic test image as numpy array
        """
        if channels == 1:
            # Grayscale gradient
            image = np.zeros((height, width), dtype=np.uint8)
            for y in range(height):
                for x in range(width):
                    image[y, x] = (x + y) % 256
        else:
            # RGB image with distinct patterns per channel
            image = np.zeros((height, width, channels), dtype=np.uint8)
            for y in range(height):
                for x in range(width):
                    image[y, x, 0] = (x * 2) % 256  # Red varies by x
                    image[y, x, 1] = (y * 2) % 256  # Green varies by y
                    if channels > 2:
                        image[y, x, 2] = ((x + y) * 2) % 256  # Blue varies by x+y

        return image

    @staticmethod
    def create_checkered_image(
        width: int = 100, height: int = 100, square_size: int = 10
    ) -> np.ndarray:
        """Create a checkered pattern image for easy verification.

        Args:
            width: Image width
            height: Image height
            square_size: Size of each checkered square

        Returns:
            Checkered pattern image
        """
        image = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            for x in range(width):
                # Create checkered pattern
                if ((x // square_size) + (y // square_size)) % 2 == 0:
                    image[y, x] = [255, 255, 255]  # White
                else:
                    image[y, x] = [0, 0, 0]  # Black
        return image


class TestCropFunction:
    """Test cases for the crop function."""

    def test_no_crop_returns_original(self):
        """Test that no cropping returns a copy of the original image."""
        original = TestImageGeneration.create_test_image(0, 0)
        crop_regions = CropRegions()  # All defaults to 0

        result = Cropping.crop(original, crop_regions)

        assert isinstance(result, CropResult)
        assert result.offset == Point(x=0, y=0)
        np.testing.assert_array_equal(result.image, original)
        assert result.image is original

    def test_percentage_crop_basic(self):
        """Test basic percentage-based cropping."""
        original = TestImageGeneration.create_test_image(100, 100)
        # Crop 10% from each side
        crop_regions = CropRegions(left=0.1, right=0.1, top=0.1, bottom=0.1)

        result = Cropping.crop(original, crop_regions)

        # Should crop 10px from each side of 100px image = 80x80 result
        assert result.image.shape == (80, 80, 3)
        assert result.offset == Point(x=10, y=10)

        # Verify the cropped content matches original
        np.testing.assert_array_equal(result.image, original[10:90, 10:90])

    def test_pixel_crop_basic(self):
        """Test basic pixel-based cropping."""
        original = TestImageGeneration.create_test_image(100, 100)
        # Crop 15px from each side
        crop_regions = CropRegions(left=15, right=15, top=15, bottom=15)

        result = Cropping.crop(original, crop_regions)

        # Should crop 15px from each side = 70x70 result
        assert result.image.shape == (70, 70, 3)
        assert result.offset == Point(x=15, y=15)

        # Verify the cropped content matches original
        np.testing.assert_array_equal(result.image, original[15:85, 15:85])

    def test_mixed_crop_types(self):
        """Test mixing percentage and pixel crop values."""
        original = TestImageGeneration.create_test_image(100, 80)
        # Mix percentages and pixels
        crop_regions = CropRegions(left=0.1, right=10, top=5, bottom=0.125)

        result = Cropping.crop(original, crop_regions)

        # left: 10% of 100 = 10px
        # right: 10px
        # top: 5px
        # bottom: 12.5% of 80 = 10px
        # Result: 80x65 (100-10-10 x 80-5-10)
        assert result.image.shape == (65, 80, 3)
        assert result.offset == Point(x=10, y=5)

        # Verify content
        np.testing.assert_array_equal(result.image, original[5:70, 10:90])

    def test_asymmetric_crop(self):
        """Test cropping different amounts from different sides."""
        original = TestImageGeneration.create_test_image(60, 80)
        crop_regions = CropRegions(left=5, right=15, top=0.1, bottom=0.2)

        result = Cropping.crop(original, crop_regions)

        # left: 5px, right: 15px, top: 8px (10% of 80), bottom: 16px (20% of 80)
        # Result: 40x56 (60-5-15 x 80-8-16)
        assert result.image.shape == (56, 40, 3)
        assert result.offset == Point(x=5, y=8)

    def test_grayscale_image(self):
        """Test cropping grayscale images."""
        original = TestImageGeneration.create_test_image(50, 50, channels=1)
        crop_regions = CropRegions(left=0.2, right=0.2, top=0.2, bottom=0.2)

        result = Cropping.crop(original, crop_regions)

        # Should be 30x30 grayscale
        assert result.image.shape == (30, 30)
        assert result.offset == Point(x=10, y=10)

    def test_empty_image_raises_error(self):
        """Test that empty image raises ValueError."""
        empty_image = np.array([])
        crop_regions = CropRegions(left=0.1)

        with pytest.raises(ValueError, match="Cannot crop empty image"):
            Cropping.crop(empty_image, crop_regions)

    def test_percentage_crop_exceeds_100_percent(self):
        """Test that percentage crop exceeding 100% raises error."""
        # This should be caught by CropRegions validation
        with pytest.raises(ValueError, match="crops >= 100% of image width"):
            CropRegions(left=0.6, right=0.5)  # 110% total

    def test_pixel_crop_exceeds_image_width(self):
        """Test that pixel crop exceeding image width raises error."""
        original = TestImageGeneration.create_test_image(100, 100)
        crop_regions = CropRegions(left=60, right=50)  # 110px total from 100px width

        with pytest.raises(ValueError, match="would crop entire image width"):
            Cropping.crop(original, crop_regions)

    def test_pixel_crop_exceeds_image_height(self):
        """Test that pixel crop exceeding image height raises error."""
        original = TestImageGeneration.create_test_image(100, 80)
        crop_regions = CropRegions(top=50, bottom=40)  # 90px total from 80px height

        with pytest.raises(ValueError, match="would crop entire image height"):
            Cropping.crop(original, crop_regions)

    def test_single_pixel_crop_exceeds_dimension(self):
        """Test that single pixel value exceeding dimension raises error."""
        original = TestImageGeneration.create_test_image(50, 50)

        with pytest.raises(ValueError, match="Left crop.*exceeds image dimension"):
            crop_regions = CropRegions(left=60)  # 60px from 50px width
            Cropping.crop(original, crop_regions)

    def test_exact_boundary_crop(self):
        """Test cropping right at the boundary (should fail)."""
        original = TestImageGeneration.create_test_image(10, 10)
        crop_regions = CropRegions(left=5, right=5)  # Exactly 100%

        with pytest.raises(ValueError, match="would crop entire image width"):
            Cropping.crop(original, crop_regions)

    def test_minimal_crop_result(self):
        """Test cropping that results in 1x1 image."""
        original = TestImageGeneration.create_test_image(3, 3)
        crop_regions = CropRegions(left=1, right=1, top=1, bottom=1)

        result = Cropping.crop(original, crop_regions)

        assert result.image.shape == (1, 1, 3)
        assert result.offset == Point(x=1, y=1)

    def test_large_image_crop(self):
        """Test cropping on larger images."""
        original = TestImageGeneration.create_test_image(1000, 800)
        crop_regions = CropRegions(left=0.1, right=0.15, top=0.05, bottom=0.2)

        result = Cropping.crop(original, crop_regions)

        # left: 100px, right: 150px, top: 40px, bottom: 160px
        # Result: 750x600
        assert result.image.shape == (600, 750, 3)
        assert result.offset == Point(x=100, y=40)

    def test_checkered_pattern_verification(self):
        """Test with checkered pattern to verify correct cropping."""
        original = TestImageGeneration.create_checkered_image(40, 40, square_size=10)
        crop_regions = CropRegions(left=10, right=10, top=10, bottom=10)

        result = Cropping.crop(original, crop_regions)

        assert result.image.shape == (20, 20, 3)
        assert result.offset == Point(x=10, y=10)

        # Verify the cropped region matches the expected part
        expected = original[10:30, 10:30]
        np.testing.assert_array_equal(result.image, expected)

    def test_string_format_crops(self):
        """Test various string format inputs."""
        original = TestImageGeneration.create_test_image(100, 100)

        # Test percentage strings
        crop_regions = CropRegions(left="10%", right="15%", top="5%", bottom="20%")
        result = Cropping.crop(original, crop_regions)
        assert result.image.shape == (75, 75, 3)  # 100-5-20 x 100-10-15

        # Test pixel strings
        crop_regions = CropRegions(left="10px", right="15px", top="5px", bottom="20px")
        result = Cropping.crop(original, crop_regions)
        assert result.image.shape == (75, 75, 3)  # Same result

        # Test mixed string formats
        crop_regions = CropRegions(left="0.1", right="15", top="5%", bottom="20px")
        result = Cropping.crop(original, crop_regions)
        assert result.image.shape == (75, 75, 3)  # Same result

    @pytest.mark.parametrize(
        "width,height", [(1, 1), (1, 100), (100, 1), (2, 2), (50, 75), (200, 150)]
    )
    def test_various_image_dimensions(self, width, height):
        """Test cropping with various image dimensions."""
        original = TestImageGeneration.create_test_image(width, height)

        # Small percentage crop that should work for any size
        crop_regions = CropRegions(left=0.1, right=0.1, top=0.1, bottom=0.1)

        if width > 2 and height > 2:  # Only test if there's room to crop
            result = Cropping.crop(original, crop_regions)

            expected_width = width - int(width * 0.1) - int(width * 0.1)
            expected_height = height - int(height * 0.1) - int(height * 0.1)

            if original.ndim == 3:
                assert result.image.shape == (
                    expected_height,
                    expected_width,
                    original.shape[2],
                )
            else:
                assert result.image.shape == (expected_height, expected_width)

    def test_crop_result_properties(self):
        """Test that CropResult has correct properties."""
        original = TestImageGeneration.create_test_image(50, 50)
        crop_regions = CropRegions(left=5, top=10)

        result = Cropping.crop(original, crop_regions)

        assert hasattr(result, "image")
        assert hasattr(result, "offset")
        assert isinstance(result.offset, Point)
        assert result.offset.x == 5
        assert result.offset.y == 10
        assert isinstance(result.image, np.ndarray)

    def test_image_data_integrity(self):
        """Test that image data is preserved correctly during cropping."""
        # Create image with known pattern
        original = np.zeros((10, 10, 3), dtype=np.uint8)
        original[5, 5] = [255, 128, 64]  # Distinctive pixel

        crop_regions = CropRegions(left=2, right=2, top=2, bottom=2)
        result = Cropping.crop(original, crop_regions)

        # The distinctive pixel should now be at position (3, 3) in cropped image
        assert result.image.shape == (6, 6, 3)
        np.testing.assert_array_equal(result.image[3, 3], [255, 128, 64])

    def test_float_precision_handling(self):
        """Test handling of floating point precision in percentage calculations."""
        original = TestImageGeneration.create_test_image(333, 333)  # Odd number
        crop_regions = CropRegions(left=1 / 3, right=1 / 3, top=0.1, bottom=0.1)

        result = Cropping.crop(original, crop_regions)

        # Should handle float precision gracefully
        left_px = int(333 * (1 / 3))  # 111
        right_px = int(333 * (1 / 3))  # 111
        top_px = int(333 * 0.1)  # 33
        bottom_px = int(333 * 0.1)  # 33

        expected_width = 333 - left_px - right_px  # 111
        expected_height = 333 - top_px - bottom_px  # 267

        assert result.image.shape == (expected_height, expected_width, 3)
