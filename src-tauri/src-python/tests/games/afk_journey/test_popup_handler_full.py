import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from adb_auto_player.games.afk_journey.popup_message_handler import (
    PopupMessage,
    PopupMessageHandler,
    PopupPreprocessResult,
)
from adb_auto_player.games.afk_journey.settings import OCREngine
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Coordinates, Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.models.ocr import OCRResult
from adb_auto_player.models.template_matching import MatchMode, TemplateMatchResult


class MockHandler(PopupMessageHandler):
    # Annotate methods that will be mocked to avoid ty-check shadowing errors
    _preprocess_screenshot_for_popup: MagicMock
    game_find_template_match: MagicMock
    find_any_template: MagicMock
    tap: MagicMock
    swipe: MagicMock
    hold: MagicMock

    def __init__(self):
        self._settings = MagicMock()
        self._settings.general.ocr_engine = OCREngine.Tesseract
        self.battle_state = MagicMock()
        self.LANG_ERROR = "error"
        self.MIN_TIMEOUT = 1

    @property
    def settings(self):
        return self._settings

    @property
    def template_dir(self):
        return MagicMock()

    def get_screenshot(self):
        return MagicMock()

    def tap(
        self,
        coordinates: Coordinates,
        scale: bool = False,
        blocking: bool = True,
        non_blocking_sleep_duration: float | None = 1 / 30,
        log_message: str | None = None,
        log: bool = True,
    ) -> None:
        pass

    def hold(
        self,
        coordinates: Coordinates,
        duration: float = 3.0,
        blocking: bool = True,
        log: bool = True,
    ) -> threading.Thread | None:
        pass

    def swipe(self, **kwargs):
        pass

    def game_find_template_match(
        self,
        template: str | Path,
        match_mode: MatchMode = MatchMode.BEST,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        screenshot: np.ndarray | None = None,
    ) -> TemplateMatchResult | None:
        return None

    def find_any_template(
        self,
        templates: list[str],
        match_mode: MatchMode = MatchMode.BEST,
        threshold: ConfidenceValue | None = None,
        grayscale: bool = False,
        crop_regions: CropRegions = CropRegions(),
        screenshot: np.ndarray | None = None,
    ) -> TemplateMatchResult | None:
        return None

    def wait_for_template(self, *args, **kwargs):
        return MagicMock()

    def wait_for_any_template(self, *args, **kwargs):
        return MagicMock()

    def _handle_popup_button(self, result, popup):
        return super()._handle_popup_button(result, popup)


class TestPopupHandlerFullCoverage:
    """Intensive coverage for PopupMessageHandler logic."""

    @patch("adb_auto_player.games.afk_journey.popup_message_handler.TesseractBackend")
    def test_handle_popup_messages_full_logic(self, mock_tesseract_class):
        """Cover handle_popup_messages loop, matching, and interaction."""
        handler = MockHandler()

        # 1. Preprocess finds a button
        preprocess_result = PopupPreprocessResult(
            original_image=np.zeros((100, 100, 3)),
            cropped_image=np.zeros((50, 50, 3)),
            crop_offset=Point(0, 0),
            button=TemplateMatchResult(
                template="navigation/confirm.png",
                confidence=ConfidenceValue(0.9),
                box=Box(Point(0, 0), 10, 10),
            ),
        )
        with patch.object(
            handler,
            "_preprocess_screenshot_for_popup",
            side_effect=[preprocess_result, None],
        ):
            # 2. OCR finds a matching message (e.g. Skip this battle?)
            mock_ocr = MagicMock()
            mock_tesseract_class.return_value = mock_ocr
            mock_ocr.detect_text_blocks.return_value = [
                OCRResult(
                    text="Skip this battle?",
                    confidence=ConfidenceValue(0.9),
                    box=Box(Point(0, 0), 1, 1),
                )
            ]

            # 3. Mock confirmation interaction
            with patch.object(handler, "tap"):
                result = handler.handle_popup_messages()
                assert result is True

    def test_preprocess_screenshot_coverage(self):
        """Cover _preprocess_screenshot_for_popup internal branches."""
        handler = MockHandler()
        # Mock screenshot
        with patch.object(
            handler,
            "get_screenshot",
            return_value=np.zeros((2000, 1000, 3), dtype=np.uint8),
        ):
            # Mock button matching via find_any_template
            match = TemplateMatchResult(
                template="navigation/confirm.png",
                confidence=ConfidenceValue(0.9),
                box=Box(Point(0, 0), 1, 1),
            )
            with patch.object(handler, "find_any_template", return_value=match):
                res = handler._preprocess_screenshot_for_popup()
                assert res is not None
                assert res.button == match

    def test_confirm_on_popup_hold_coverage(self):
        """Cover _handle_popup_button with hold_to_confirm=True."""
        handler = MockHandler()

        msg = PopupMessage(
            text="Hold Test",
            confirm_button_template="test.png",
            hold_to_confirm=True,
            hold_duration_seconds=1.0,
        )

        with patch.object(handler, "hold") as mock_hold:
            with patch.object(
                handler,
                "game_find_template_match",
                return_value=TemplateMatchResult(
                    template="test.png",
                    confidence=ConfidenceValue(0.9),
                    box=Box(Point(0, 0), 1, 1),
                ),
            ):
                res = PopupPreprocessResult(
                    original_image=np.zeros((100, 100, 3)),
                    cropped_image=np.zeros((50, 50, 3)),
                    crop_offset=Point(0, 0),
                    button=TemplateMatchResult(
                        template="other.png",
                        confidence=ConfidenceValue(0.9),
                        box=Box(Point(0, 0), 1, 1),
                    ),
                )
                handler._handle_popup_button(res, msg)
                mock_hold.assert_called()

    def test_handle_popup_messages_no_match_coverage(self):
        """Cover the case where no message matches the OCR text."""
        handler = MockHandler()
        preprocess_result = PopupPreprocessResult(
            original_image=np.zeros((100, 100, 3)),
            cropped_image=np.zeros((50, 50, 3)),
            crop_offset=Point(0, 0),
            button=TemplateMatchResult(
                template="navigation/confirm.png",
                confidence=ConfidenceValue(0.9),
                box=Box(Point(0, 0), 10, 10),
            ),
        )
        with patch.object(
            handler,
            "_preprocess_screenshot_for_popup",
            side_effect=[preprocess_result, None],
        ):
            with patch(
                "adb_auto_player.games.afk_journey.popup_message_handler.TesseractBackend"
            ) as mock_tess:
                mock_ocr = MagicMock()
                mock_tess.return_value = mock_ocr
                mock_ocr.detect_text_blocks.return_value = [
                    OCRResult(
                        text="Unknown random text",
                        confidence=ConfidenceValue(0.9),
                        box=Box(Point(0, 0), 1, 1),
                    )
                ]
                result = handler.handle_popup_messages()
                assert result is False

    def test_unknown_popup_saves_debug_screenshot(self, tmp_path):
        """Unrecognized popups (empty or non-matching OCR) save a screenshot."""
        handler = MockHandler()
        screenshot = np.zeros((100, 100, 3), dtype=np.uint8)
        preprocess_result = PopupPreprocessResult(
            original_image=screenshot,
            cropped_image=np.zeros((50, 50, 3)),
            crop_offset=Point(0, 0),
            button=TemplateMatchResult(
                template="navigation/confirm.png",
                confidence=ConfidenceValue(0.9),
                box=Box(Point(0, 0), 10, 10),
            ),
        )
        with patch(
            "adb_auto_player.game._screenshot_mixin.SettingsLoader.get_app_config_dir",
            return_value=tmp_path,
        ):
            result = handler._get_popup_message_from_ocr_results([], preprocess_result)

        assert result is None
        saved_dir = tmp_path / "data" / "screenshots" / "unknown_popups"
        assert saved_dir.exists()
        assert len(list(saved_dir.glob("unknown_popups_*.png"))) == 1

    def test_unknown_popup_screenshot_save_failure_is_logged(self, caplog):
        """A failure to save the debug screenshot must not raise."""
        handler = MockHandler()
        with patch(
            "adb_auto_player.game._screenshot_mixin.SettingsLoader.get_app_config_dir",
            side_effect=RuntimeError("App Config Dir undefined"),
        ):
            handler.save_debug_screenshot(np.zeros((10, 10, 3)), "unknown_popups")
        assert "Could not save debug screenshot" in caplog.text

    def test_mock_handler_unused_methods_coverage(self):
        """Call all stubbed methods in MockHandler for coverage."""
        handler = MockHandler()
        # Call properties
        _ = handler.template_dir
        # Call methods
        handler.get_screenshot()
        handler.tap(Point(0, 0))
        handler.hold(Point(0, 0))
        handler.swipe(start=Point(0, 0), end=Point(1, 1))
        handler.game_find_template_match("test.png")
        handler.find_any_template(["test.png"])
        handler.wait_for_template("test.png")
        handler.wait_for_any_template(["test.png"])
