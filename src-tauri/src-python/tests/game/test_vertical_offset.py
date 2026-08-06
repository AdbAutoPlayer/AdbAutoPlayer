"""Tests for the per-device vertical screen offset correction.

Covers `_ScreenshotMixin._apply_vertical_offset_to_screenshot`
(screenshot-space correction) and `_InputMixin._apply_vertical_offset` (its
inverse, applied before tapping/swiping/holding on the real device).
"""

from unittest.mock import MagicMock, patch

import numpy as np
from adb_auto_player.game._input_mixin import _InputMixin
from adb_auto_player.game._screenshot_mixin import _ScreenshotMixin
from adb_auto_player.models.geometry import Point


def _make_rows_image(num_rows: int) -> np.ndarray:
    """Build a (num_rows, 1, 1) image where each row's value is its index."""
    return np.arange(num_rows, dtype=np.uint8).reshape(num_rows, 1, 1)


class TestScreenshotVerticalOffset:
    """Tests for `_ScreenshotMixin._apply_vertical_offset_to_screenshot`."""

    def test_zero_offset_returns_image_unchanged(self):
        image = _make_rows_image(6)
        with patch(
            "adb_auto_player.game._screenshot_mixin.SettingsLoader.adb_settings"
        ) as mock_settings:
            mock_settings.return_value.device.vertical_offset = 0
            result = _ScreenshotMixin._apply_vertical_offset_to_screenshot(image)
        np.testing.assert_array_equal(result, image)

    def test_positive_offset_crops_top_and_pads_bottom(self):
        image = _make_rows_image(6)
        with patch(
            "adb_auto_player.game._screenshot_mixin.SettingsLoader.adb_settings"
        ) as mock_settings:
            mock_settings.return_value.device.vertical_offset = 2
            result = _ScreenshotMixin._apply_vertical_offset_to_screenshot(image)
        assert result.shape == image.shape
        # Content shifts up: rows [2,3,4,5] then the last row repeated twice.
        np.testing.assert_array_equal(
            result.flatten(), np.array([2, 3, 4, 5, 5, 5], dtype=np.uint8)
        )

    def test_negative_offset_pads_top_and_crops_bottom(self):
        image = _make_rows_image(6)
        with patch(
            "adb_auto_player.game._screenshot_mixin.SettingsLoader.adb_settings"
        ) as mock_settings:
            mock_settings.return_value.device.vertical_offset = -2
            result = _ScreenshotMixin._apply_vertical_offset_to_screenshot(image)
        assert result.shape == image.shape
        # Content shifts down: the first row repeated twice, then [0,1,2,3].
        np.testing.assert_array_equal(
            result.flatten(), np.array([0, 0, 0, 1, 2, 3], dtype=np.uint8)
        )


class TestInputVerticalOffset:
    """Tests for `_InputMixin._apply_vertical_offset`."""

    def test_zero_offset_returns_same_point(self):
        point = Point(100, 200)
        with patch(
            "adb_auto_player.game._input_mixin.SettingsLoader.adb_settings"
        ) as mock_settings:
            mock_settings.return_value.device.vertical_offset = 0
            result = _InputMixin._apply_vertical_offset(point)
        assert (result.x, result.y) == (100, 200)

    def test_positive_offset_shifts_y_down(self):
        point = Point(100, 200)
        with patch(
            "adb_auto_player.game._input_mixin.SettingsLoader.adb_settings"
        ) as mock_settings:
            mock_settings.return_value.device.vertical_offset = 40
            result = _InputMixin._apply_vertical_offset(point)
        assert (result.x, result.y) == (100, 240)

    def test_negative_offset_shifts_y_up(self):
        point = Point(100, 200)
        with patch(
            "adb_auto_player.game._input_mixin.SettingsLoader.adb_settings"
        ) as mock_settings:
            mock_settings.return_value.device.vertical_offset = -40
            result = _InputMixin._apply_vertical_offset(point)
        assert (result.x, result.y) == (100, 160)


class TestSaveDebugScreenshot:
    """Tests for `_ScreenshotMixin.save_debug_screenshot`."""

    def test_saves_screenshot_to_category_subfolder(self, tmp_path):
        # _ScreenshotMixin's _GameBase parent is abstract; the method under
        # test doesn't touch `self`, so a mock instance is enough here.
        mock_instance = MagicMock(spec=_ScreenshotMixin)
        screenshot = np.zeros((10, 10, 3), dtype=np.uint8)
        with patch(
            "adb_auto_player.game._screenshot_mixin.SettingsLoader.get_app_config_dir",
            return_value=tmp_path,
        ):
            _ScreenshotMixin.save_debug_screenshot(
                mock_instance, screenshot, "navigation_failed"
            )

        saved_dir = tmp_path / "data" / "screenshots" / "navigation_failed"
        assert saved_dir.exists()
        assert len(list(saved_dir.glob("navigation_failed_*.png"))) == 1

    def test_save_failure_is_logged_not_raised(self, caplog):
        mock_instance = MagicMock(spec=_ScreenshotMixin)
        with patch(
            "adb_auto_player.game._screenshot_mixin.SettingsLoader.get_app_config_dir",
            side_effect=RuntimeError("App Config Dir undefined"),
        ):
            _ScreenshotMixin.save_debug_screenshot(
                mock_instance, np.zeros((10, 10, 3)), "navigation_failed"
            )
        assert "Could not save debug screenshot" in caplog.text


class _CombinedLikeGame(_InputMixin, _ScreenshotMixin):
    """Mirrors `Game`'s mixin order: `_InputMixin` before `_ScreenshotMixin`."""


class TestVerticalOffsetMethodsDoNotCollideAcrossMixins:
    """Regression test for a mixin method-name collision.

    `Game` inherits both mixins; identically-named methods would collide in
    the MRO, silently shadowing one implementation with the other.
    """

    def test_each_mixin_method_resolves_to_its_own_implementation(self):
        assert (
            _CombinedLikeGame._apply_vertical_offset
            is _InputMixin._apply_vertical_offset
        )
        assert (
            _CombinedLikeGame._apply_vertical_offset_to_screenshot
            is _ScreenshotMixin._apply_vertical_offset_to_screenshot
        )

    def test_screenshot_offset_applies_correctly_through_combined_mro(self):
        image = _make_rows_image(6)
        with patch(
            "adb_auto_player.game._screenshot_mixin.SettingsLoader.adb_settings"
        ) as mock_settings:
            mock_settings.return_value.device.vertical_offset = 2
            result = _CombinedLikeGame._apply_vertical_offset_to_screenshot(image)
        np.testing.assert_array_equal(
            result.flatten(), np.array([2, 3, 4, 5, 5, 5], dtype=np.uint8)
        )

    def test_input_offset_applies_correctly_through_combined_mro(self):
        point = Point(100, 200)
        with patch(
            "adb_auto_player.game._input_mixin.SettingsLoader.adb_settings"
        ) as mock_settings:
            mock_settings.return_value.device.vertical_offset = 40
            result = _CombinedLikeGame._apply_vertical_offset(point)
        assert (result.x, result.y) == (100, 240)
