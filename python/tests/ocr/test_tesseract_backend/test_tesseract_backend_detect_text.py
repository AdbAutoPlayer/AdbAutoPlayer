import numpy as np
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box
from adb_auto_player.models.ocr import OCRResult


class TestTesseractBackendDetectText:
    """Test the detect_text function."""

    def test_detect_text_basic(self, tesseract_backend, simple_text_image):
        """Test basic text detection with bounding boxes."""
        results = tesseract_backend.detect_text(simple_text_image)

        assert isinstance(results, list)
        assert len(results) > 0

        for result in results:
            assert isinstance(result, OCRResult)
            assert isinstance(result.text, str)
            assert len(result.text.strip()) > 0
            assert isinstance(result.confidence, ConfidenceValue)
            assert isinstance(result.box, Box)
            assert result.box.width > 0
            assert result.box.height > 0

    def test_detect_text_with_confidence_threshold(
        self, tesseract_backend, simple_text_image
    ):
        """Test text detection with confidence threshold."""
        high_confidence = ConfidenceValue(80)
        low_confidence = ConfidenceValue(10)

        high_results = tesseract_backend.detect_text(
            simple_text_image, min_confidence=high_confidence
        )
        low_results = tesseract_backend.detect_text(
            simple_text_image, min_confidence=low_confidence
        )

        assert isinstance(high_results, list)
        assert isinstance(low_results, list)
        # Low confidence should return same or more results
        assert len(low_results) >= len(high_results)

    def test_detect_text_bounding_boxes(self, tesseract_backend, simple_text_image):
        """Test that bounding boxes are reasonable."""
        results = tesseract_backend.detect_text(simple_text_image)

        image_height, image_width = simple_text_image.shape[:2]

        for result in results:
            box = result.box
            # Boxes should be within image bounds
            assert 0 <= box.top_left.x < image_width
            assert 0 <= box.top_left.y < image_height
            assert box.top_left.x + box.width <= image_width
            assert box.top_left.y + box.height <= image_height

    def test_detect_text_empty_image(self, tesseract_backend):
        """Test text detection on empty image."""
        blank_image = np.ones((100, 100, 3), dtype=np.uint8) * 255

        results = tesseract_backend.detect_text(blank_image)

        assert isinstance(results, list)
        # Should return empty list or very few/no valid detections
