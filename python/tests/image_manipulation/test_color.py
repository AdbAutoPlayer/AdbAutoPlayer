import cv2
import numpy as np
import pytest
from adb_auto_player.image_manipulation import (
    ColorFormat,
    is_grayscale,
    to_bgr,
    to_grayscale,
    to_rgb,
)


class TestColor:
    def test_is_grayscale_true_and_false(self):
        gray_img = np.zeros((10, 10), dtype=np.uint8)
        color_img = np.zeros((10, 10, 3), dtype=np.uint8)

        assert is_grayscale(gray_img) is True
        assert is_grayscale(color_img) is False

    def test_to_grayscale_already_grayscale(self):
        gray_img = np.random.randint(0, 256, (5, 5), dtype=np.uint8)
        # Should return the same image unchanged
        out = to_grayscale(gray_img)
        np.testing.assert_array_equal(out, gray_img)

    def test_to_grayscale_bgr_and_rgb_conversion(self):
        # Create a synthetic BGR color image (blue dominant)
        bgr_img = np.zeros((5, 5, 3), dtype=np.uint8)
        bgr_img[..., 0] = 255  # Blue channel max

        # Convert BGR to grayscale using the function
        gray_from_bgr = to_grayscale(bgr_img, ColorFormat.BGR)
        # Reference conversion using OpenCV directly for comparison
        expected_gray = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2GRAY)
        np.testing.assert_array_equal(gray_from_bgr, expected_gray)

        # Create synthetic RGB image (red dominant)
        rgb_img = np.zeros((5, 5, 3), dtype=np.uint8)
        rgb_img[..., 0] = 255  # Red channel max

        gray_from_rgb = to_grayscale(rgb_img, ColorFormat.RGB)
        expected_gray_rgb = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2GRAY)
        np.testing.assert_array_equal(gray_from_rgb, expected_gray_rgb)

    def test_to_grayscale_invalid_input_shape(self):
        # 4-channel image
        img_4ch = np.zeros((5, 5, 4), dtype=np.uint8)
        # 1D array
        img_1d = np.zeros((5,), dtype=np.uint8)

        with pytest.raises(ValueError):
            to_grayscale(img_4ch)
        with pytest.raises(ValueError):
            to_grayscale(img_1d)

    def test_to_grayscale_unsupported_color_format(self):
        color_img = np.zeros((5, 5, 3), dtype=np.uint8)
        with pytest.raises(ValueError):
            to_grayscale(color_img, color_format="XYZ")  # invalid enum value

    def test_to_rgb_valid_and_invalid(self):
        bgr_img = np.zeros((5, 5, 3), dtype=np.uint8)
        rgb_img = to_rgb(bgr_img)
        expected_rgb = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
        np.testing.assert_array_equal(rgb_img, expected_rgb)

        # Invalid inputs
        invalid_img = np.zeros((5, 5), dtype=np.uint8)
        with pytest.raises(ValueError):
            to_rgb(invalid_img)
        invalid_img2 = np.zeros((5, 5, 4), dtype=np.uint8)
        with pytest.raises(ValueError):
            to_rgb(invalid_img2)

    def test_to_bgr_valid_and_invalid(self):
        rgb_img = np.zeros((5, 5, 3), dtype=np.uint8)
        bgr_img = to_bgr(rgb_img)
        expected_bgr = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2BGR)
        np.testing.assert_array_equal(bgr_img, expected_bgr)

        # Invalid inputs
        invalid_img = np.zeros((5, 5), dtype=np.uint8)
        with pytest.raises(ValueError):
            to_bgr(invalid_img)
        invalid_img2 = np.zeros((5, 5, 4), dtype=np.uint8)
        with pytest.raises(ValueError):
            to_bgr(invalid_img2)
