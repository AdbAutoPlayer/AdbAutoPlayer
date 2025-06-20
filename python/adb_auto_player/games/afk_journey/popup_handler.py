import logging
import time
from abc import ABC
from dataclasses import dataclass

import cv2
import numpy as np
from adb_auto_player import Game
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.template_matching import MatchMode, TemplateMatchResult
from adb_auto_player.ocr import PSM, TesseractBackend, TesseractConfig


@dataclass(frozen=True)
class PopupMessage:
    text: str
    # This will be clicked or held
    confirm_button_template: str = "navigation/confirm.png"
    click_dont_remind_me: bool = False
    hold_to_confirm: bool = False
    hold_duration_seconds: float = 5.0


# You do not actually need to add the whole text of the Popup Message
# A snippet works.
popup_messages: list[PopupMessage] = [
    PopupMessage(
        text="Are you sure you want to exit the game",
        # Does not have "remind me" checkbox
    ),
    PopupMessage(
        text=(
            "No hero is placed on the Talent Buff Tile. "
            "Do you want to start the battle anyways?"
        ),
        click_dont_remind_me=True,
    ),
    PopupMessage(
        text=(
            "You haven't actiovated any Season Faction Talent."
            # Do you want to start the battle anyway?
        ),
        click_dont_remind_me=True,
    ),
    PopupMessage(
        text="Your formation is incomplete.",
        # There are 2 different messages for this
        # "Your formation is incomplete. Begin battle anyway?"
        # "Your formation is incomplete. Turn on Auto Battle mode anyway? ..."
        click_dont_remind_me=True,
    ),
    PopupMessage(
        text="You are currently fishing.",
        # If you quit this fishing attempt will fail. Quit anyway?
        # Does not have "remind me" checkbox
    ),
    PopupMessage(
        text="End the exploration",
        confirm_button_template="arcane_labyrinth/hold_to_exit.png",
        hold_to_confirm=True,
        hold_duration_seconds=5.0,
        # Does not have "remind me" checkbox
    ),
    PopupMessage(
        text="Skip this battle?",
        # Does not have "remind me" checkbox
    ),
]


@dataclass(frozen=True)
class PopupPreprocessResult:
    cropped_image: np.ndarray
    crop_offset: Point
    button: TemplateMatchResult
    dont_remind_me_checkbox: TemplateMatchResult | None = None


class AFKJourneyPopupHandler(Game, ABC):
    def handle_confirmation_popups(self) -> None:
        """Handles multiple popups."""
        max_popups = 5
        count = 0
        while count < max_popups and self._handle_confirmation_popup():
            count += 1

    def _handle_confirmation_popup(self) -> bool:
        """Confirm popups.

        Returns:
            bool: True if confirmed, False if not.
        """
        # PSM 6 - Single Block of Text works best here.
        ocr = TesseractBackend(config=TesseractConfig(psm=PSM.SINGLE_BLOCK))
        image = self.get_screenshot()
        preprocess_result = self._preprocess_for_popup(image)
        if not preprocess_result:
            return False

        ocr_results = ocr.detect_text_blocks(
            image=preprocess_result.cropped_image, min_confidence=ConfidenceValue("80%")
        )
        # This is actually not needed in this scenario because we do not need
        # The coordinates or boundaries of the text
        # Leaving this for demo though.
        ocr_results = [
            result.with_offset(preprocess_result.crop_offset) for result in ocr_results
        ]

        matching_popup: PopupMessage | None = None
        for i, result in enumerate(ocr_results):
            matching_popup = next(
                (popup for popup in popup_messages if popup.text in result.text), None
            )
            if matching_popup:
                break

        if not matching_popup:
            logging.error(f"Unknown popup detected: {ocr_results}")
            return False

        if matching_popup.click_dont_remind_me:
            if preprocess_result.dont_remind_me_checkbox:
                logging.info(
                    "Don't remind me checkbox: "
                    f"{preprocess_result.dont_remind_me_checkbox}"
                )
                self.tap(preprocess_result.dont_remind_me_checkbox)
                time.sleep(1)
            else:
                logging.warning("Don't remind me checkbox expected but not found.")

        return self._handled_popup_button(
            preprocess_result,
            matching_popup,
            image,
        )

    def _handled_popup_button(
        self,
        result: PopupPreprocessResult,
        popup: PopupMessage,
        image: np.ndarray,
    ) -> bool:
        if result.button.template == popup.confirm_button_template:
            button: TemplateMatchResult | None = result.button
        else:
            button = self.game_find_template_match(
                template=popup.confirm_button_template,
                screenshot=image,
            )

        if not button:
            return False

        if popup.hold_to_confirm:
            self.hold(coordinates=button, duration=popup.hold_duration_seconds)
        else:
            self.tap(coordinates=button)
        time.sleep(3)
        return True

    def _preprocess_for_popup(self, image: np.ndarray) -> PopupPreprocessResult | None:
        height, width = image.shape[:2]

        height_5_percent = int(0.05 * height)
        height_35_percent = int(0.35 * height)

        if button := self.find_any_template(
            templates=[
                "navigation/confirm.png",
                "navigation/continue_top_right_corner.png",
            ],
            threshold=0.8,
            crop_regions=CropRegions(left=0.5, top=0.4),
            screenshot=image,
        ):
            crop_bottom = button.box.top - height_5_percent
        else:
            # No button detected this cannot be a supported popup.
            return None

        if checkbox := self.game_find_template_match(
            template="popup/checkbox_unchecked.png",
            match_mode=MatchMode.TOP_LEFT,
            threshold=0.8,
            crop_regions=CropRegions(right=0.8, top=0.2, bottom=0.6),
            screenshot=image,
        ):
            crop_top = checkbox.box.bottom + height_5_percent
        else:
            # based on my estimations this should work unless there is a popup
            # that is more than 8 lines of text which I do not think there is.
            crop_top = height_35_percent

        image = image[crop_top:crop_bottom, 0:width]
        image = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        return PopupPreprocessResult(
            cropped_image=image,
            crop_offset=Point(0, crop_top),  # No left crop applied, only top,
            button=button,
            dont_remind_me_checkbox=checkbox,
        )
