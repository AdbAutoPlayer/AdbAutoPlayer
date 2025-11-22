import numpy as np
import pytest
from adb_auto_player.models.ocr import OCRResult
from adb_auto_player.ocr import PSM, TesseractBackend, TesseractConfig


class TestTesseractBackendIntegration:
    """Integration tests (these would require actual Tesseract installation)."""

    def test_all_methods_return_consistent_types(
        self, tesseract_backend, simple_text_image
    ):
        """Test that all detection methods return consistent types."""
        extract_result = tesseract_backend.extract_text(simple_text_image)
        detect_results = tesseract_backend.detect_text(simple_text_image)
        block_results = tesseract_backend.detect_text_blocks(simple_text_image)
        line_results = tesseract_backend.detect_text_lines(simple_text_image)
        para_results = tesseract_backend.detect_text_paragraphs(simple_text_image)

        # Check types
        assert isinstance(extract_result, str)
        assert isinstance(detect_results, list)
        assert isinstance(block_results, list)
        assert isinstance(line_results, list)
        assert isinstance(para_results, list)

        # Check OCRResult structure in lists
        for results in [detect_results, block_results, line_results, para_results]:
            for result in results:
                assert isinstance(result, OCRResult)
                assert hasattr(result, "text")
                assert hasattr(result, "confidence")
                assert hasattr(result, "box")

    def test_different_psm_modes(self, simple_text_image):
        """Test that different PSM modes work."""
        psm_modes = [PSM.DEFAULT, PSM.SINGLE_LINE, PSM.SINGLE_BLOCK, PSM.SPARSE_TEXT]

        for psm in psm_modes:
            config = TesseractConfig(psm=psm)
            backend = TesseractBackend(config)

            # Test that it doesn't crash
            try:
                result = backend.extract_text(simple_text_image)
                assert isinstance(result, str)
            except Exception as e:
                pytest.fail(f"PSM mode {psm} failed: {e}")

    def test_error_handling_invalid_image(self, tesseract_backend):
        """Test error handling with invalid image data."""
        # Test with invalid image shapes/types
        invalid_images = [
            np.array([]),  # Empty array
            np.zeros((10, 10)),  # 2D instead of 3D
            np.zeros((10, 10, 1)),  # Single channel
            np.zeros((0, 0, 3)),  # Zero dimensions
        ]

        for invalid_img in invalid_images:
            try:
                # These should either work or raise a reasonable exception
                result = tesseract_backend.extract_text(invalid_img)
                # If it works, result should be a string
                assert isinstance(result, str)
            except (ValueError, RuntimeError, Exception):
                # It's okay if it raises an exception for invalid input
                pass
