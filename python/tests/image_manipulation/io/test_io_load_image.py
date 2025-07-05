from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from adb_auto_player.image_manipulation.io import IO, template_cache


def synthetic_image(shape=(10, 10, 3)):
    return np.ones(shape, dtype=np.uint8) * 255


class TestLoadImage:
    @patch("adb_auto_player.image_manipulation.io.cv2.imdecode")
    @patch("adb_auto_player.image_manipulation.io.np.fromfile")
    def test_load_image_basic(self, mock_fromfile, mock_imdecode):
        dummy_bytes = np.array([0, 1, 2], dtype=np.uint8)
        mock_fromfile.return_value = dummy_bytes

        dummy_image = synthetic_image()
        mock_imdecode.return_value = dummy_image

        path = Path("image.png")
        result = IO.load_image(path)

        assert np.array_equal(result, dummy_image)

    @patch("adb_auto_player.image_manipulation.io.cv2.imdecode")
    def test_load_image_cache_hit(self, mock_imdecode):
        img = synthetic_image()
        path = Path("cached.png")
        key = f"{path}_1.0_grayscale=False"
        template_cache[key] = img

        result = IO.load_image(path)

        mock_imdecode.assert_not_called()
        assert np.array_equal(result, img)

        # Clean cache after test to avoid side effects
        template_cache.clear()

    @patch("adb_auto_player.image_manipulation.io.cv2.imdecode")
    @patch("adb_auto_player.image_manipulation.io.np.fromfile")
    def test_load_image_file_not_found(self, mock_fromfile, mock_imdecode):
        dummy_bytes = np.array([0, 1, 2], dtype=np.uint8)
        mock_fromfile.return_value = dummy_bytes
        mock_imdecode.return_value = None  # Simulate failure to decode

        path = Path("nonexistent.png")

        with pytest.raises(FileNotFoundError):
            IO.load_image(path)

    @patch("adb_auto_player.image_manipulation.io.cv2.resize")
    @patch("adb_auto_player.image_manipulation.io.cv2.imdecode")
    @patch("adb_auto_player.image_manipulation.io.np.fromfile")
    def test_load_image_scale(self, mock_fromfile, mock_imdecode, mock_resize):
        dummy_bytes = np.array([0, 1, 2], dtype=np.uint8)
        mock_fromfile.return_value = dummy_bytes

        img = synthetic_image(shape=(20, 30, 3))
        mock_imdecode.return_value = img

        scaled_img = np.ones((10, 15, 3), dtype=np.uint8)
        mock_resize.return_value = scaled_img

        path = Path("image.png")
        scale = 0.5

        result = IO.load_image(path, image_scale_factor=scale)

        mock_resize.assert_called_once_with(
            img,
            (int(30 * scale), int(20 * scale)),
            interpolation=mock_resize.call_args[1]["interpolation"],
        )
        assert np.array_equal(result, scaled_img)

    @patch("adb_auto_player.image_manipulation.color.Color.to_grayscale")
    @patch("adb_auto_player.image_manipulation.io.cv2.imdecode")
    @patch("adb_auto_player.image_manipulation.io.np.fromfile")
    def test_load_image_grayscale(self, mock_fromfile, mock_imdecode, mock_to_gray):
        dummy_bytes = np.array([0, 1, 2], dtype=np.uint8)
        mock_fromfile.return_value = dummy_bytes

        img = synthetic_image()
        mock_imdecode.return_value = img

        gray_img = np.full((10, 10), 128, dtype=np.uint8)
        mock_to_gray.return_value = gray_img

        path = Path("img.png")

        result = IO.load_image(path, grayscale=True)

        mock_to_gray.assert_called_once_with(img)
        assert np.array_equal(result, gray_img)
