from functools import cached_property
from unittest.mock import MagicMock, patch

import numpy as np
from adb_auto_player.games.afk_journey.popup_message_handler import (
    PopupMessageHandler,
    PopupPreprocessResult,
)
from adb_auto_player.games.afk_journey.settings import OCREngine
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.template_matching import TemplateMatchResult


class MockPopupHandler(PopupMessageHandler):
    def __init__(self):
        self._settings = MagicMock()
        self._settings.general.ocr_engine = OCREngine.Tesseract

    @property
    def settings(self):
        return self._settings

    @cached_property
    def template_dir(self):
        return MagicMock()


class TestPopupHandlerOCR:
    """Test the OCR dispatching logic in PopupMessageHandler."""

    @patch("adb_auto_player.games.afk_journey.popup_message_handler.TesseractBackend")
    def test_run_popup_ocr_tesseract(self, mock_tesseract_class):
        """Test that Tesseract is used by default or when configured."""
        handler = MockPopupHandler()
        handler.settings.general.ocr_engine = OCREngine.Tesseract

        mock_ocr = MagicMock()
        mock_tesseract_class.return_value = mock_ocr

        preprocess_result = PopupPreprocessResult(
            original_image=np.zeros((100, 100, 3)),
            cropped_image=np.zeros((50, 50, 3)),
            crop_offset=Point(0, 0),
            button=TemplateMatchResult(
                template="test.png",
                confidence=ConfidenceValue(0.9),
                box=Box(Point(0, 0), 10, 10),
            ),
        )

        handler._run_popup_ocr(preprocess_result)

        mock_tesseract_class.assert_called_once()
        mock_ocr.detect_text_blocks.assert_called_once()

    @patch("adb_auto_player.games.afk_journey.popup_message_handler.RapidOCRBackend")
    def test_run_popup_ocr_rapidocr(self, mock_rapidocr_class):
        """Test that RapidOCR is used when configured."""
        handler = MockPopupHandler()
        handler.settings.general.ocr_engine = OCREngine.RapidOCR

        mock_ocr = MagicMock()
        mock_rapidocr_class.return_value = mock_ocr

        preprocess_result = PopupPreprocessResult(
            original_image=np.zeros((100, 100, 3)),
            cropped_image=np.zeros((50, 50, 3)),
            crop_offset=Point(0, 0),
            button=TemplateMatchResult(
                template="test.png",
                confidence=ConfidenceValue(0.9),
                box=Box(Point(0, 0), 10, 10),
            ),
        )

        handler._run_popup_ocr(preprocess_result)

        mock_rapidocr_class.assert_called_once()
        mock_ocr.detect_text_blocks.assert_called_once()

    @patch("adb_auto_player.games.afk_journey.popup_message_handler.TesseractBackend")
    def test_run_popup_ocr_fallback(self, mock_tesseract_class):
        """Test fallback to Tesseract on settings error."""
        handler = MockPopupHandler()
        # Mock settings to raise an exception when accessing general
        type(handler.settings).general = property(
            lambda x: exec('raise Exception("Settings error")')
        )

        mock_ocr = MagicMock()
        mock_tesseract_class.return_value = mock_ocr

        preprocess_result = PopupPreprocessResult(
            original_image=np.zeros((100, 100, 3)),
            cropped_image=np.zeros((50, 50, 3)),
            crop_offset=Point(0, 0),
            button=TemplateMatchResult(
                template="test.png",
                confidence=ConfidenceValue(0.9),
                box=Box(Point(0, 0), 10, 10),
            ),
        )

        handler._run_popup_ocr(preprocess_result)

        # Should fallback to Tesseract
        mock_tesseract_class.assert_called_once()

    def test_mock_popup_handler_coverage(self):
        """Call stubbed methods in MockPopupHandler for coverage."""
        handler = MockPopupHandler()
        _ = handler.template_dir
