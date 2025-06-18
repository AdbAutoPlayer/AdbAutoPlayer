import logging
import time
from dataclasses import dataclass

import cv2
import numpy as np
from adb_auto_player import Coordinates
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.games.afk_journey.base import AFKJourneyBase
from adb_auto_player.models.geometry.box import Box
from adb_auto_player.models.geometry.point import Point
from adb_auto_player.models.template_matching.TemplateMatchResult import (
    TemplateMatchResult,
)
from adb_auto_player.models.threshold import Threshold
from adb_auto_player.ocr.tesseract_backend import TesseractBackend
from adb_auto_player.ocr.tesseract_config import TesseractConfig
from adb_auto_player.ocr.tesseract_psm import PSM
from adb_auto_player.template_matching import (
    CropRegions,
    MatchMode,
)


@dataclass(frozen=True)
class PopupMessage:
    text: str
    # This will be clicked or held
    confirm_button_template: str = "navigation/confirm.png"
    click_dont_remind_me: bool = False
    hold_to_confirm: bool = False
    hold_duration_seconds: float = 3.0


popup_messages: list[PopupMessage] = [
    PopupMessage(
        text="Are you sure you want to exit the game",
    ),
    PopupMessage(
        text=(
            "No hero is placed on the Talent Buff Tile. "
            "Do you want to start the battle anyways?"
        ),
        click_dont_remind_me=True,
    ),
    PopupMessage(
        text="Your formation is incomplete. Begin battle anyway?",
        click_dont_remind_me=True,
    ),
]


@dataclass(frozen=True)
class PopupPreprocessResult:
    cropped_image: np.ndarray
    crop_offset: Point
    button: Box
    dont_remind_me_checkbox: Box | None = None


class AFKJourneyPopupHandler(AFKJourneyBase):
    @register_command(
        gui=GuiMetadata(label="OCR Popup Test", tooltip="Test this please")
    )
    def test_popup(self) -> None:
        logging.info("=== Start OCR Popup Test ===")
        self.start_up(device_streaming=True)
        start_time = time.time()
        self.handle_confirmation_popup()
        total_duration = time.time() - start_time
        logging.info(f"Total duration: {total_duration:.3f}s")
        logging.info("=== End OCR Popup Test ===")

    def handle_confirmation_popup(self) -> bool:
        """Confirm popups.

        Returns:
            bool: True if confirmed, False if not.
        """
        # PSM 6 - Single Block of Text works best here.
        ocr = TesseractBackend(config=TesseractConfig(psm=PSM.SINGLE_BLOCK))
        preprocess_result = self._preprocess_for_popup(self.get_screenshot())
        if not preprocess_result:
            logging.warning("No Confirmation Popup detected.")
            return False

        ocr_results = ocr.detect_text_blocks(
            image=preprocess_result.cropped_image, min_confidence=Threshold("80%")
        )

        # This is actually not needed in this scenario because we do not need
        # The coordinates or boundaries of the text
        # Leaving this for demo though.
        ocr_results = [
            result.with_offset(preprocess_result.crop_offset) for result in ocr_results
        ]

        logging.info(f"Found {len(ocr_results)} text blocks:")
        for i, result in enumerate(ocr_results):
            logging.info(f"  [{i}] {result!s}")

        if preprocess_result.dont_remind_me_checkbox:
            logging.info(
                f"Don't remind me checkbox: {preprocess_result.dont_remind_me_checkbox}"
            )
            # TODO need to update tap to accept Point
            center = preprocess_result.dont_remind_me_checkbox.center
            self.tap(Coordinates(center.x, center.y))
        else:
            logging.warning("Don't remind me checkbox not found.")

        logging.info(f"Button: {preprocess_result.button}")
        logging.info("Not actually clicking the button for testing.")
        return True

    def _preprocess_for_popup(self, image: np.ndarray) -> PopupPreprocessResult | None:
        height, width = image.shape[:2]

        # remove 5% of top and bottom
        height_5_percent = int(0.05 * height)

        # Should return Box or TemplateMatchResult objects in the future
        if confirm := self.find_any_template(
            templates=[
                "navigation/confirm.png",
                "navigation/continue_top_right_corner.png",
            ],
            threshold=0.8,
            crop=CropRegions(left=0.5, top=0.4),
            screenshot=image,
        ):
            # template match should return TemplateMatchResult in the future.
            # then this line can be removed
            button = self._convert_to_template_match_result(confirm).box
            # button = confirm.box
            crop_bottom = button.top - height_5_percent
        else:
            # No button detected this cannot be a supported popup.
            return None

        if checkbox := self.game_find_template_match(
            template="popup/checkbox_unchecked.png",
            match_mode=MatchMode.TOP_LEFT,
            threshold=0.8,
            crop=CropRegions(right=0.8, top=0.2, bottom=0.6),
            screenshot=image,
        ):
            # dont_remind_me_checkbox = checkbox.box
            # could be removed if function returned a TemplateMatchResult
            x, y = checkbox
            dont_remind_me_checkbox = self._convert_to_template_match_result(
                ("popup/checkbox_unchecked.png", x, y)
            ).box
            crop_top = dont_remind_me_checkbox.bottom + height_5_percent
        else:
            dont_remind_me_checkbox = None
            crop_top = height_5_percent

        image = image[crop_top:crop_bottom, 0:width]
        image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        return PopupPreprocessResult(
            cropped_image=image,
            crop_offset=Point(0, crop_top),  # No left crop applied, only top,
            button=button,
            dont_remind_me_checkbox=dont_remind_me_checkbox,
        )

    def _convert_to_template_match_result(self, result_tuple: tuple[str, int, int]):
        """Temporary will be removed once properly implemented."""
        template, x, y = result_tuple
        return TemplateMatchResult(
            template=template,
            box=self._point_to_3x3_box(point=Point(x, y)),
            confidence=1.0,  # doesn't really matter here.
        )

    def _point_to_3x3_box(self, point: Point) -> Box:
        """Convert a point to a 3x3 box with the point at the center.

        Temporary function while TemplateMatching does not return proper Result objects.

        Args:
            point: The point to be centered in the box

        Returns:
            Box: A 3x3 box with the given point at its center

        Raises:
            ValueError: If the resulting box would have negative coordinates
        """
        # Calculate the top-left corner (point is at center of 3x3 box)
        top_left_x = point.x - 1
        top_left_y = point.y - 1

        # Ensure the box doesn't go into negative coordinates
        if top_left_x < 0 or top_left_y < 0:
            raise ValueError(
                f"Cannot create 3x3 box centered at {point} - "
                f"would result in negative coordinates: "
                f"top_left=({top_left_x}, {top_left_y})"
            )

        top_left = Point(top_left_x, top_left_y)
        return Box(top_left=top_left, width=3, height=3)
