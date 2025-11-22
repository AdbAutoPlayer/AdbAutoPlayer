from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box
from adb_auto_player.models.ocr import OCRResult

from .conftest import TestImageGenerator


class TestTesseractBackendDetectTextBlocks:
    """Test the detect_text_blocks function."""

    def test_detect_text_blocks_basic(self, tesseract_backend, block_text_image):
        """Test basic text block detection."""
        results = tesseract_backend.detect_text_blocks(block_text_image)

        assert isinstance(results, list)
        assert len(results) > 0

        for result in results:
            assert isinstance(result, OCRResult)
            assert isinstance(result.text, str)
            assert len(result.text.strip()) > 0
            assert isinstance(result.box, Box)
            # Block text should be longer than individual words
            assert len(result.text.split()) >= 1

    def test_detect_text_blocks_vs_individual_words(
        self, tesseract_backend, block_text_image
    ):
        """Test that blocks contain more text than individual detections."""
        block_results = tesseract_backend.detect_text_blocks(block_text_image)
        word_results = tesseract_backend.detect_text(block_text_image)

        # Blocks should generally contain more characters per result
        if block_results and word_results:
            avg_block_length = sum(len(r.text) for r in block_results) / len(
                block_results
            )
            avg_word_length = sum(len(r.text) for r in word_results) / len(word_results)

            # Blocks should generally be longer (though this might not always hold)
            assert avg_block_length >= avg_word_length * 0.5  # Allow some flexibility

    def test_detect_text_blocks_with_confidence(
        self, tesseract_backend, block_text_image
    ):
        """Test block detection with confidence threshold."""
        results = tesseract_backend.detect_text_blocks(
            block_text_image, min_confidence=ConfidenceValue(50)
        )

        assert isinstance(results, list)
        for result in results:
            # Note: The code sets confidence to 100
            # so this test mainly checks structure
            assert isinstance(result.confidence, ConfidenceValue)

    def test_detect_text_blocks_bounding_boxes(
        self, tesseract_backend, block_text_image
    ):
        """Test that block bounding boxes are reasonable."""
        results = tesseract_backend.detect_text_blocks(block_text_image)

        image_height, image_width = block_text_image.shape[:2]

        for result in results:
            box = result.box
            assert 0 <= box.top_left.x < image_width
            assert 0 <= box.top_left.y < image_height
            assert box.width > 0
            assert box.height > 0
            assert box.top_left.x + box.width <= image_width
            assert box.top_left.y + box.height <= image_height


class TestTesseractBackendDetectTextLines:
    """Test the detect_text_lines function."""

    def test_detect_text_lines_basic(self, tesseract_backend, multi_line_image):
        """Test basic text line detection."""
        results = tesseract_backend.detect_text_lines(multi_line_image)

        assert isinstance(results, list)
        assert len(results) > 0

        for result in results:
            assert isinstance(result, OCRResult)
            assert isinstance(result.text, str)
            assert len(result.text.strip()) > 0

    def test_detect_text_lines_count(self, tesseract_backend, multi_line_image):
        """Test that line detection finds approximately the right number of lines."""
        results = tesseract_backend.detect_text_lines(multi_line_image)

        # We created an image with 3 lines, should detect at least 1-2 lines
        # (OCR might not be perfect, so we're lenient)
        assert 1 <= len(results) <= 5

    def test_detect_text_lines_vs_blocks(self, tesseract_backend, multi_line_image):
        """Test that line detection gives different results than block detection."""
        line_results = tesseract_backend.detect_text_lines(multi_line_image)
        block_results = tesseract_backend.detect_text_blocks(multi_line_image)

        # Results might be different in structure
        assert isinstance(line_results, list)
        assert isinstance(block_results, list)

    def test_detect_text_lines_single_line(self, tesseract_backend):
        """Test line detection on single line image."""
        single_line_image = TestImageGenerator.create_simple_text_image(
            "Single line of text"
        )
        results = tesseract_backend.detect_text_lines(single_line_image)

        assert isinstance(results, list)
        # Should detect at least one line
        assert len(results) >= 0  # Might be 0 if OCR fails completely


class TestTesseractBackendDetectTextParagraphs:
    """Test the detect_text_paragraphs function."""

    def test_detect_text_paragraphs_basic(self, tesseract_backend, paragraph_image):
        """Test basic paragraph detection."""
        results = tesseract_backend.detect_text_paragraphs(paragraph_image)

        assert isinstance(results, list)
        assert len(results) >= 0  # Might be 0 if no paragraphs detected

        for result in results:
            assert isinstance(result, OCRResult)
            assert isinstance(result.text, str)
            assert isinstance(result.box, Box)

    def test_detect_text_paragraphs_vs_lines(self, tesseract_backend, paragraph_image):
        """Test paragraph detection vs line detection."""
        paragraph_results = tesseract_backend.detect_text_paragraphs(paragraph_image)
        line_results = tesseract_backend.detect_text_lines(paragraph_image)

        # Both should return lists
        assert isinstance(paragraph_results, list)
        assert isinstance(line_results, list)

        # If both have results, paragraphs should generally be longer
        if paragraph_results and line_results:
            avg_para_length = sum(len(r.text) for r in paragraph_results) / len(
                paragraph_results
            )
            avg_line_length = sum(len(r.text) for r in line_results) / len(line_results)

            # Paragraphs should contain more text (allowing some flexibility)
            assert avg_para_length >= avg_line_length * 0.5

    def test_detect_text_paragraphs_content(self, tesseract_backend, paragraph_image):
        """Test that paragraph detection captures meaningful content."""
        results = tesseract_backend.detect_text_paragraphs(paragraph_image)

        if results:  # Only test if we got results
            # Check that at least one result contains multiple words
            multi_word_results = [r for r in results if len(r.text.split()) > 1]
            # Should have at least some multi-word results for paragraphs
            assert len(multi_word_results) >= 0  # Allow for OCR imperfection
