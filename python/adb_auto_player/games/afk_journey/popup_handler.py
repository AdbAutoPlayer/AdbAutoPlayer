import logging
import time

import cv2
import numpy as np

from adb_auto_player.decorators.register_command import register_command, GuiMetadata
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.models.threshold import Threshold
from adb_auto_player.ocr.tesseract_backend import TesseractBackend
from adb_auto_player.ocr.tesseract_config import TesseractConfig
from adb_auto_player.ocr.tesseract_psm import PSM
from adb_auto_player.template_matching import crop_image, CropRegions, \
    find_template_match, MatchMode


class AFKJourneyPopupHandler(AFKJourneyBase):
    @register_command(
        gui=GuiMetadata(
            label="OCR Popup Test",
            tooltip="Test this please"
        )
    )
    def test_popup(self) -> None:
        self.start_up(device_streaming=True)
        logging.info("=== Start OCR Popup Test ===")
        logging.info("Starting Tesseract")
        ocr = TesseractBackend(
            config=TesseractConfig(
                psm=PSM.SINGLE_BLOCK
            )
        )

        start_time = time.time()
        screenshot = self._preprocess_popup(self.get_screenshot())
        preprocess_duration = time.time() - start_time
        results = ocr.detect_text_blocks(
            screenshot, min_confidence=Threshold("80%")
        )
        ocr_duration = time.time() - preprocess_duration

        # TODO log preprocess duration, ocr duration, total duration
        # TODO log results
        for result in results:
            # TODO log result.text, result.confidence, result.box
            pass

        return

    def _preprocess_popup(
        self, image: np.ndarray,
    ) -> np.ndarray:
        checkbox_image = self._load_image("popup/checkbox_unchecked.png")
        confirm_button = self._load_image("navigation/confirm.png")


        height, width = image.shape[:2]

        # Get the checkbox position
        cropped_image, left, top = crop_image(
            image, CropRegions(right=0.8, top=0.2, bottom=0.6)
        )
        checkbox = find_template_match(
            base_image=cropped_image,
            template_image=checkbox_image,
            match_mode=MatchMode.TOP_LEFT,
            threshold=0.8,
        )

        y_checkbox = 0
        if checkbox:
            x_checkbox, y_checkbox = checkbox
            x_checkbox += left
            y_checkbox += top

        # Get the confirm button position
        cropped_image, left, top = crop_image(
            image,
            CropRegions(left=0.5, top=0.4),
        )

        confirm_button = find_template_match(
            base_image=cropped_image,
            template_image=confirm_button,
            threshold=0.8,
        )
        y_confirm = height
        if confirm_button:
            x_confirm, y_confirm = confirm_button
            x_confirm += left
            y_confirm += top

        # 5 % = 96
        image = image[y_checkbox + 96 : y_confirm - 96, 0:width]

        grayscale = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        return grayscale