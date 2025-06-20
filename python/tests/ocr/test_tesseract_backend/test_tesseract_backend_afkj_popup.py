"""Unit tests for OCR backends with performance benchmarking."""

import time
import unittest
from pathlib import Path

import cv2
import numpy as np
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.ocr import PSM, TesseractBackend, TesseractConfig


class TestTesseractBackendAFKJPopup(unittest.TestCase):
    """Test cases for OCR backend implementations."""

    tesseract_backend = TesseractBackend()

    @staticmethod
    def _get_bgr_image(filename: str) -> np.ndarray:
        """Return test image.

        Returns:
            np.ndarray: Test image
        """
        path = Path(__file__).parent / "data" / filename
        return cv2.imread(path.as_posix())

    def test_handle_checkbox_popup_no_preprocessing(self):
        tesseract_backend = TesseractBackend(
            config=TesseractConfig(
                psm=PSM.SINGLE_BLOCK
            )  # PSM 6 works best in this case
        )

        no_hero_on_talent_buff_popup = TestTesseractBackendAFKJPopup._get_bgr_image(
            "popup_no_hero_placed_talent_buff_tile.png"
        )

        text_detected = False

        start_time = time.time()
        results = tesseract_backend.detect_text_blocks(
            no_hero_on_talent_buff_popup, min_confidence=ConfidenceValue("90%")
        )
        duration = time.time() - start_time
        print(f"\ndetect_text_blocks without preprocessing took {duration:.4f} seconds")

        for result in results:
            if "No hero is placed on the Talent Buff Tile" in result.text:
                text_detected = True

        self.assertTrue(text_detected)

    def test_handle_checkbox_popup_grayscale(self):
        tesseract_backend = TesseractBackend(
            config=TesseractConfig(
                psm=PSM.SINGLE_BLOCK
            )  # PSM 6 works best in this case
        )

        no_hero_on_talent_buff_popup = TestTesseractBackendAFKJPopup._get_bgr_image(
            "popup_no_hero_placed_talent_buff_tile.png"
        )

        text_detected = False

        start_time = time.time()
        no_hero_on_talent_buff_popup = cv2.cvtColor(
            no_hero_on_talent_buff_popup,
            cv2.COLOR_BGR2GRAY,
        )

        results = tesseract_backend.detect_text_blocks(
            no_hero_on_talent_buff_popup, min_confidence=ConfidenceValue("90%")
        )
        duration = time.time() - start_time
        print(f"\ndetect_text_blocks grayscale {duration:.4f} seconds")

        for result in results:
            if "No hero is placed on the Talent Buff Tile" in result.text:
                text_detected = True

        self.assertTrue(text_detected)
