"""Unit tests for OCR backends with performance benchmarking."""

import time
import unittest
from pathlib import Path

import cv2
import numpy as np
from adb_auto_player.image_manipulation import crop
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import MatchMode
from adb_auto_player.ocr import PSM, TesseractBackend, TesseractConfig
from adb_auto_player.template_matching import (
    find_template_match,
)


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

    def test_handle_checkbox_popup_with_preprocessing(self):
        tesseract_backend = TesseractBackend(
            config=TesseractConfig(
                psm=PSM.SINGLE_BLOCK
            )  # PSM 6 works best in this case
        )

        no_hero_on_talent_buff_popup = TestTesseractBackendAFKJPopup._get_bgr_image(
            "popup_no_hero_placed_talent_buff_tile.png"
        )

        text_detected = False

        # Loading the images before start time because they would typically be cached.
        checkbox_unchecked = TestTesseractBackendAFKJPopup._get_bgr_image(
            "checkbox_unchecked.png"
        )
        confirm = TestTesseractBackendAFKJPopup._get_bgr_image("confirm.png")

        start_time = time.time()
        no_hero_on_talent_buff_popup = self._preprocess_popup(
            no_hero_on_talent_buff_popup, checkbox_unchecked, confirm
        )
        results = tesseract_backend.detect_text_blocks(
            no_hero_on_talent_buff_popup, min_confidence=ConfidenceValue("80%")
        )
        duration = time.time() - start_time
        print(f"\ndetect_text_blocks with preprocessing took {duration:.4f} seconds")

        for result in results:
            if "No hero is placed on the Talent Buff Tile" in result.text:
                text_detected = True

        self.assertTrue(text_detected)

    def _preprocess_popup(
        self,
        image: np.ndarray,
        checkbox_image: np.ndarray,
        confirm_button: np.ndarray,
    ) -> np.ndarray:
        height, width = image.shape[:2]

        # Get the checkbox position
        result = crop(image, CropRegions(right=0.8, top=0.2, bottom=0.6))
        checkbox = find_template_match(
            base_image=result.image,
            template_image=checkbox_image,
            match_mode=MatchMode.TOP_LEFT,
            threshold=0.8,
        )
        y_checkbox = 0
        if checkbox:
            x_checkbox, y_checkbox = checkbox
            x_checkbox += result.offset.x
            y_checkbox += result.offset.y

        # Get the confirm button position
        result = crop(
            image,
            CropRegions(left=0.5, top=0.4),
        )

        confirm_button = find_template_match(
            base_image=result.image,
            template_image=confirm_button,
            threshold=0.8,
        )
        y_confirm = height
        if confirm_button:
            x_confirm, y_confirm = confirm_button
            x_confirm += result.offset.x
            y_confirm += result.offset.y

        # 5 % = 96
        image = image[y_checkbox + 96 : y_confirm - 96, 0:width]

        grayscale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        return grayscale
