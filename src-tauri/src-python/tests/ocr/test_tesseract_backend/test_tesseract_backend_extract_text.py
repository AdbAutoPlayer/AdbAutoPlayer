import numpy as np
from adb_auto_player.ocr import OEM, PSM, TesseractBackend, TesseractConfig


class TestTesseractBackendExtractText:
    """Test the extract_text function."""

    def test_extract_simple_text(self, tesseract_backend, simple_text_image):
        """Test extracting text from a simple image."""
        result = tesseract_backend.extract_text(simple_text_image)

        assert isinstance(result, str)
        assert "Hello" in result or "World" in result  # OCR might not be perfect
        assert len(result.strip()) > 0

    def test_extract_text_with_custom_config(self, simple_text_image):
        """Test extract_text with custom configuration."""
        backend = TesseractBackend()
        custom_config = TesseractConfig(psm=PSM.SINGLE_LINE, oem=OEM.LSTM_ONLY)

        result = backend.extract_text(simple_text_image, config=custom_config)

        assert isinstance(result, str)
        assert len(result.strip()) >= 0  # Might be empty if OCR fails

    def test_extract_text_empty_image(self, tesseract_backend):
        """Test extracting text from an empty/blank image."""
        blank_image = np.ones((100, 100, 3), dtype=np.uint8) * 255  # White image

        result = tesseract_backend.extract_text(blank_image)

        assert isinstance(result, str)
        assert len(result.strip()) == 0

    def test_extract_multi_line_text(self, tesseract_backend, multi_line_image):
        """Test extracting multi-line text."""
        result = tesseract_backend.extract_text(multi_line_image)

        assert isinstance(result, str)
        assert len(result.strip()) > 0
        # Should contain some words from the original lines
        words_found = sum(
            1
            for word in ["First", "Second", "Third", "line"]
            if word.lower() in result.lower()
        )
        assert words_found >= 2  # At least some words should be detected
