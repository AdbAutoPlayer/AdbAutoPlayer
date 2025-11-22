import cv2
import numpy as np
import pytest
from adb_auto_player.image_manipulation import IO


class TestGetBGRNpArrayFromPNGBytes:
    @staticmethod
    def create_test_png_bytes() -> bytes:
        """Creates a 1x1 black PNG image and returns its byte representation."""
        img = np.zeros((1, 1, 3), dtype=np.uint8)
        success, buffer = cv2.imencode(".png", img)
        if not success:
            raise RuntimeError("Failed to encode PNG image")
        return buffer.tobytes()

    def test_valid_png_bytes(self):
        png_bytes = self.create_test_png_bytes()
        result = IO.get_bgr_np_array_from_png_bytes(png_bytes)
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 1, 3)
        assert np.all(result == 0)

    def test_png_with_warning_prefix(self):
        png_bytes = self.create_test_png_bytes()
        prefixed_data = b"WARNING: something went wrong\n" + png_bytes
        result = IO.get_bgr_np_array_from_png_bytes(prefixed_data)
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 1, 3)
        assert np.all(result == 0)

    def test_invalid_png_bytes_raises_value_error(self):
        with pytest.raises(ValueError, match="Failed to decode screenshot image data"):
            IO.get_bgr_np_array_from_png_bytes(b"not a real png")

    def test_no_png_header_raises_value_error(self):
        # Remove the PNG header from otherwise valid PNG bytes
        png_bytes = self.create_test_png_bytes()
        corrupted_bytes = png_bytes[8:]  # Cut off the PNG header
        with pytest.raises(ValueError, match="Failed to decode screenshot image data"):
            IO.get_bgr_np_array_from_png_bytes(corrupted_bytes)
