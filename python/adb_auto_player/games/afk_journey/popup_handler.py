import logging
import time

import cv2
import numpy as np
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.models.geometry.point import Point
from adb_auto_player.models.threshold import Threshold
from adb_auto_player.ocr.tesseract_backend import TesseractBackend
from adb_auto_player.ocr.tesseract_config import TesseractConfig
from adb_auto_player.ocr.tesseract_psm import PSM
from adb_auto_player.template_matching import (
    CropRegions,
    MatchMode,
    crop_image,
)


class AFKJourneyPopupHandler(AFKJourneyBase):
    @register_command(
        gui=GuiMetadata(label="OCR Popup Test", tooltip="Test this please")
    )
    def test_popup(self) -> None:
        logging.info("=== Start OCR Popup Test ===")
        self.start_up(device_streaming=True)
        logging.info("Populating Cache...")
        self._populate_cache()
        logging.info("Starting Tesseract...")
        ocr = TesseractBackend(config=TesseractConfig(psm=PSM.SINGLE_BLOCK))

        start_time = time.time()
        screenshot, offset = self._preprocess_popup(self.get_screenshot())
        logging.info(f"Offset: {offset}")
        preprocess_time = time.time()
        preprocess_duration = preprocess_time - start_time
        ocr_results = ocr.detect_text_blocks(
            screenshot, min_confidence=Threshold("80%")
        )
        ocr_results = [result.with_offset(offset) for result in ocr_results]

        total_time = time.time()
        ocr_duration = total_time - preprocess_time
        total_duration = total_time - start_time

        logging.info(f"Preprocess duration: {preprocess_duration:.3f}s")
        logging.info(f"OCR duration: {ocr_duration:.3f}s")
        logging.info(f"Total duration: {total_duration:.3f}s")

        logging.info(f"Found {len(ocr_results)} text blocks:")
        for i, result in enumerate(ocr_results):
            logging.info(f"  [{i}] {result!s}")

        logging.info("=== End OCR Popup Test ===")

    def _populate_cache(self):
        templates = [
            "navigation/confirm.png",
            "navigation/continue.png",
            "popup/checkbox_unchecked.png",
        ]
        for template in templates:
            self._load_image(template)

    def _preprocess_popup(
        self,
        image: np.ndarray,
    ) -> tuple[np.ndarray, Point]:
        height, width = image.shape[:2]
        # remove 5% of top and bottom
        crop_top = 96
        crop_bottom = height - 96

        checkbox = self.game_find_template_match(
            template="popup/checkbox_unchecked.png",
            match_mode=MatchMode.TOP_LEFT,
            threshold=0.8,
            crop=CropRegions(right=0.8, top=0.2, bottom=0.6),
            screenshot=image,
        )

        if checkbox:
            x_checkbox, y_checkbox = checkbox
            crop_top = y_checkbox + 96
        else:
            logging.warning("Checkbox not found.")

        cropped_image, left, top = crop_image(
            image,
            CropRegions(left=0.5, top=0.4),
        )

        # Get the confirm button position
        confirm = self.find_any_template(
            templates=[
                "navigation/confirm.png",
                "navigation/continue.png",
            ],
            threshold=0.8,
            crop=CropRegions(left=0.5, top=0.4),
        )
        if confirm:
            _, x_confirm, y_confirm = confirm
            crop_bottom = y_confirm - 96
        else:
            logging.error("Confirm button not found.")

        image = image[crop_top:crop_bottom, 0:width]

        grayscale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        return grayscale, Point(0, crop_top)  # No left crop applied, only top
