import logging
import re
import time
from abc import ABC
from dataclasses import dataclass, replace

import numpy as np
from adb_auto_player.exceptions import AutoPlayerWarningError
from adb_auto_player.game import Game
from adb_auto_player.image_manipulation import Color, ColorFormat
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.ocr import OCRResult
from adb_auto_player.models.template_matching import MatchMode, TemplateMatchResult
from adb_auto_player.ocr import PSM, TesseractBackend, TesseractConfig
from adb_auto_player.util import StringHelper


@dataclass(frozen=True)
class PopupMessage:
    text: str
    # This will be clicked or held
    confirm_button_template: str = "navigation/confirm.png"
    has_dont_remind_me: bool = False
    hold_to_confirm: bool = False
    hold_duration_seconds: float = 5.0
    ignore: bool = False
    strip_numbers: bool = False
    raise_exception_before_confirming: Exception | None = None
    raise_exception_after_confirming: Exception | None = None


season_talent_messages = [
    PopupMessage(
        # You haven't activated any Season Faction Talent.
        # Do you want to start the battle anyway?
        text="You haven't activated any Season Faction Talent",
        has_dont_remind_me=True,
    ),
    PopupMessage(
        # No hero is placed on the Talent Buff Tile.
        # Do you want to start the battle anyways?
        text="No hero is placed on the Talent Buff Tile",
        has_dont_remind_me=True,
    ),
]

general_battle_messages = [
    PopupMessage(
        text="Skip this battle?",
    ),
    PopupMessage(
        # There are 2 different messages for this
        # "Your formation is incomplete. Begin battle anyway?"
        # "Your formation is incomplete. Turn on Auto Battle mode anyway? ..."
        text="Your formation is incomplete",
    ),
]

arena_messages = [
    PopupMessage(
        # Daily attempts: x/5
        text="Spend to purchase Warrior's Guarantee",
        ignore=True,
    ),
]

arcane_labyrinth_messages = [
    PopupMessage(
        # You won't receive any rewards for attempting this difficulty outside of
        # the event period. Do you still want to start your exploration?
        text="Do you still want to start your exploration?",
        has_dont_remind_me=False,  # I think it does not have one
    ),
    PopupMessage(
        text="End the exploration",
        confirm_button_template="arcane_labyrinth/hold_to_exit.png",
        hold_to_confirm=True,
        hold_duration_seconds=5.0,
    ),
]

duras_trials_messages = [
    PopupMessage(
        # You have made multiple attempts.
        # Keep challenging this stage?
        # Challenge Attempts: x
        text="Keep challenging this stage?",
    ),
    PopupMessage(
        # Spend x to challenge this stage again?
        text="Spend to challenge",
        ignore=True,  # handled elsewhere
        strip_numbers=True,
        # possibly appears in other places
    ),
    PopupMessage(
        # Multiple attempts made. Please wait for the reset.
        text="Please wait for the reset",
        raise_exception_after_confirming=AutoPlayerWarningError(
            "All attempts used, have to wait for reset."
        ),
    ),
    PopupMessage(
        text="Blessed Heroes are not deployed",
        has_dont_remind_me=True,
    ),
]

misc_messages = [
    PopupMessage(
        # Emporium
        text="Confirm to use Diamonds?",
        ignore=True,
    ),
    PopupMessage(
        # could just throw an exception here
        text="Daily Instant AFK attempt limit reached",
        # Daily Instant AFK attempt limit reached.
        # Available again after the cooldown ends.
        ignore=True,
    ),
    PopupMessage(
        # Are you sure you want to exit the game?
        text="Are you sure you want to exit the",
        confirm_button_template="navigation/x.png",
    ),
    PopupMessage(
        text="Exit the game",
        confirm_button_template="navigation/x.png",
    ),
]

fishing_messages = [
    PopupMessage(
        # You are currently fishing.
        # If you quit this fishing attempt will fail. Quit anyway?
        text="You are currently fishing",
    ),
]

legend_trial_messages = [
    PopupMessage(
        text="Legend Trial has been refreshed",
        raise_exception_after_confirming=AutoPlayerWarningError(
            "Legend Trial has been refreshed."
        ),
    ),
]

HEAD_FROM_WORLD_TO_HOMESTEAD_MESSAGE = PopupMessage(
    # Heading to the Homestead now. Continue?
    text="Heading to Homestead now",
    # Default we don't want to enter homestead
    confirm_button_template="navigation/x.png",
)
HEAD_FROM_HOMESTEAD_TO_WORLD_MESSAGE = PopupMessage(
    # Heading to World now. Continue?
    text="Heading to World now",
    # Default we don't want to enter homestead
    confirm_button_template="navigation/confirm.png",
)

# Combine all messages into one list
popup_messages: list[PopupMessage] = (
    season_talent_messages
    + general_battle_messages
    + arena_messages
    + arcane_labyrinth_messages
    + duras_trials_messages
    + misc_messages
    + fishing_messages
    + legend_trial_messages
    + [
        HEAD_FROM_HOMESTEAD_TO_WORLD_MESSAGE,
        HEAD_FROM_WORLD_TO_HOMESTEAD_MESSAGE,
    ]
)


@dataclass(frozen=True)
class PopupPreprocessResult:
    original_image: np.ndarray
    cropped_image: np.ndarray
    crop_offset: Point
    button: TemplateMatchResult
    dont_remind_me_checkbox: TemplateMatchResult | None = None


class PopupMessageHandler(Game, ABC):
    def handle_popup_messages(
        self,
        navigate_to_homestead: bool = False,
    ) -> bool:
        """Handles multiple popups."""
        max_popups = 5
        count = 0

        result = False
        while count < max_popups and self._handle_confirmation_popup(
            navigate_to_homestead
        ):
            count += 1
            result = True
        return result

    def _get_popup_message_from_ocr_results(
        self, ocr_results: list[OCRResult]
    ) -> PopupMessage | None:
        for i, result in enumerate(ocr_results):
            if matching_popup := PopupMessageHandler._find_matching_popup(result.text):
                return matching_popup

        logging.warning(
            "Unknown popup detected, "
            f"please post on Discord so it can be added: {ocr_results}"
        )
        return None

    def _handle_confirmation_popup(
        self,
        navigate_to_homestead: bool = False,
    ) -> PopupMessage | None:
        """Confirm popups.

        Returns:
            bool: True if confirmed, False if not.
        """
        preprocess_result = self._preprocess_screenshot_for_popup()
        if not preprocess_result:
            return None

        # PSM 6 - Single Block of Text works best here.
        ocr = TesseractBackend(config=TesseractConfig(psm=PSM.SINGLE_BLOCK))
        ocr_results = ocr.detect_text_blocks(
            image=preprocess_result.cropped_image, min_confidence=ConfidenceValue("80%")
        )
        # This is actually not needed in this scenario because we do not need
        # The coordinates or boundaries of the text
        # Leaving this for demo though.
        ocr_results = [
            result.with_offset(preprocess_result.crop_offset) for result in ocr_results
        ]

        matching_popup = self._get_popup_message_from_ocr_results(ocr_results)
        if not matching_popup:
            return None

        if navigate_to_homestead:
            if matching_popup == HEAD_FROM_WORLD_TO_HOMESTEAD_MESSAGE:
                matching_popup = replace(
                    HEAD_FROM_WORLD_TO_HOMESTEAD_MESSAGE,
                    confirm_button_template="navigation/confirm.png",
                )
            elif matching_popup == HEAD_FROM_HOMESTEAD_TO_WORLD_MESSAGE:
                matching_popup = replace(
                    HEAD_FROM_HOMESTEAD_TO_WORLD_MESSAGE,
                    confirm_button_template="navigation/x.png",
                )

        if matching_popup.raise_exception_before_confirming:
            raise matching_popup.raise_exception_before_confirming

        if matching_popup.ignore:
            return None

        if matching_popup.has_dont_remind_me:
            if preprocess_result.dont_remind_me_checkbox:
                self.tap(preprocess_result.dont_remind_me_checkbox)
                time.sleep(1)
            else:
                logging.warning("Don't remind me checkbox expected but not found.")

        popup_message = self._handle_popup_button(
            preprocess_result,
            matching_popup,
        )

        if matching_popup.raise_exception_after_confirming:
            raise matching_popup.raise_exception_after_confirming

        return popup_message

    def _handle_popup_button(
        self,
        result: PopupPreprocessResult,
        popup: PopupMessage,
    ) -> PopupMessage | None:
        if result.button.template == popup.confirm_button_template:
            button: TemplateMatchResult | None = result.button
        else:
            button = self.game_find_template_match(
                template=popup.confirm_button_template,
                screenshot=result.original_image,
            )

        if not button:
            return None

        if popup.hold_to_confirm:
            self.hold(coordinates=button, duration=popup.hold_duration_seconds)
        else:
            self.tap(coordinates=button)
        time.sleep(3)
        return popup

    def _preprocess_screenshot_for_popup(self) -> PopupPreprocessResult | None:
        screenshot = self.get_screenshot()
        image = screenshot.copy()
        height, width = image.shape[:2]

        height_5_percent = int(0.05 * height)
        height_35_percent = int(0.35 * height)

        if button := self.find_any_template(
            templates=[
                "navigation/confirm.png",
                "navigation/continue_top_right_corner.png",
            ],
            threshold=ConfidenceValue("80%"),
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
            threshold=ConfidenceValue("80%"),
            crop_regions=CropRegions(right=0.8, top=0.2, bottom=0.6),
            screenshot=image,
        ):
            crop_top = checkbox.box.bottom + height_5_percent
        else:
            # based on my estimations this should work unless there is a popup
            # that is more than 8 lines of text which I do not think there is.
            crop_top = height_35_percent

        image = image[crop_top:crop_bottom, 0:width]
        image = Color.to_grayscale(image, ColorFormat.BGR)

        return PopupPreprocessResult(
            original_image=screenshot,
            cropped_image=image,
            crop_offset=Point(0, crop_top),  # No left crop applied, only top,
            button=button,
            dont_remind_me_checkbox=checkbox,
        )

    @staticmethod
    def _find_matching_popup(
        ocr_text: str, similarity_threshold: ConfidenceValue = ConfidenceValue("80%")
    ) -> PopupMessage | None:
        """Find matching popup message using fuzzy substring matching.

        Args:
            ocr_text: Text detected by OCR
            similarity_threshold: Minimum similarity ratio for fuzzy matching

        Returns:
            PopupMessage or None if no match found
        """
        for popup in popup_messages:
            if PopupMessageHandler._popup_fuzzy_substring_search(
                ocr_text,
                popup,
                similarity_threshold,
            ):
                return popup
        return None

    @staticmethod
    def _popup_fuzzy_substring_search(
        text: str,
        popup: PopupMessage,
        similarity_threshold: ConfidenceValue = ConfidenceValue("80%"),
    ) -> bool:
        pattern = popup.text
        if popup.strip_numbers:
            text = re.sub(r"\d+", "", text)
            text = re.sub(r"\s+", " ", text)
            text = text.strip()

        if StringHelper.fuzzy_substring_match(
            text,
            pattern,
            similarity_threshold,
        ):
            return True
        return False
