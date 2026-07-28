"""Tests for `AdbController._resolve_display_ids`.

Covers the multi-display detection used to pick the display that is actually
running the game, instead of adb's ambiguous defaults. Regression test for:
some emulators (observed on MuMuPlayer's Android 15 image) expose several
virtual displays. `screencap` with no `-d` can capture an unrelated idle
display (e.g. the Android home screen), and `input` (tap/back/swipe) follows
whichever display currently has system input focus — which can drift to a
*different* display than the one screenshots are being captured from (e.g.
input landing on a home-screen icon while the bot's screenshot still shows
the game). Both cases leave the bot blind or acting on the wrong screen.
"""

from unittest.mock import MagicMock

from adb_auto_player.device.adb.adb_controller import AdbController
from adb_auto_player.models.geometry import Point

_DUMPSYS_DISPLAY_SINGLE = """
  mViewports=[DisplayViewport{displayId=0, uniqueId='local:4619827820427265280'}]
"""

_DUMPSYS_DISPLAY_MULTI = """
  mViewports=[DisplayViewport{displayId=0, uniqueId='local:4619827820427265280'}, DisplayViewport{displayId=2, uniqueId='local:4619827767814508545'}, DisplayViewport{displayId=3, uniqueId='local:4619826888814064386'}]
"""  # noqa: E501

_DUMPSYS_WINDOW_DISPLAYS_MULTI = """
  Display: mDisplayId=3 (organized)
  displayId=3
  Display: mDisplayId=0 (organized)
  displayId=0
  Display: mDisplayId=2 (organized)
  displayId=2
      * Task{visible=true A=10052:com.farlightgames.igame.gp}
"""


def _make_controller(shell_side_effect) -> tuple[AdbController, MagicMock]:
    """Build an AdbController with a mocked device wrapper.

    Returns:
        tuple[AdbController, MagicMock]: The controller, and the mock assigned to
            its `.d` — kept as its own properly-typed reference so assertions on
            it (`.assert_called_with`, `.call_count`, ...) don't go through
            `controller.d`, which the type checker still sees as `AdbDeviceWrapper`.
    """
    controller = AdbController.__new__(AdbController)
    mock_d = MagicMock()
    mock_d.shell.side_effect = shell_side_effect
    controller.d = mock_d
    controller._screenshot_display_id = None
    controller._input_display_id = None
    controller._display_ids_resolved = False
    return controller, mock_d


class TestResolveDisplayIds:
    """Tests for `AdbController._resolve_display_ids`."""

    def test_single_display_returns_none_none(self):
        controller, _ = _make_controller([_DUMPSYS_DISPLAY_SINGLE])
        result = controller._resolve_display_ids(["com.farlightgames.igame.gp"])
        assert result == (None, None)

    def test_multi_display_resolves_physical_and_wm_id_hosting_game(self):
        controller, _ = _make_controller(
            [_DUMPSYS_DISPLAY_MULTI, _DUMPSYS_WINDOW_DISPLAYS_MULTI]
        )
        result = controller._resolve_display_ids(["com.farlightgames.igame.gp"])
        assert result == ("4619827767814508545", "2")

    def test_multi_display_no_matching_package_returns_none_none(self):
        controller, _ = _make_controller(
            [_DUMPSYS_DISPLAY_MULTI, _DUMPSYS_WINDOW_DISPLAYS_MULTI]
        )
        result = controller._resolve_display_ids(["com.other.app"])
        assert result == (None, None)

    def test_no_package_prefixes_returns_none_none(self):
        controller, _ = _make_controller([_DUMPSYS_DISPLAY_MULTI])
        result = controller._resolve_display_ids([])
        assert result == (None, None)

    def test_screenshot_caches_resolved_display_ids(self):
        controller, mock_d = _make_controller(
            [_DUMPSYS_DISPLAY_MULTI, _DUMPSYS_WINDOW_DISPLAYS_MULTI]
        )
        mock_d.screenshot.return_value = b"png-bytes"

        first = controller.screenshot(["com.farlightgames.igame.gp"])
        second = controller.screenshot(["com.farlightgames.igame.gp"])

        assert first == b"png-bytes"
        assert second == b"png-bytes"
        # dumpsys is only queried once, screenshot is captured twice.
        assert mock_d.shell.call_count == 2
        assert mock_d.screenshot.call_count == 2
        mock_d.screenshot.assert_called_with(display_id="4619827767814508545")
        assert controller._input_display_id == "2"

    def test_tap_uses_resolved_input_display_id(self):
        controller, mock_d = _make_controller(
            [_DUMPSYS_DISPLAY_MULTI, _DUMPSYS_WINDOW_DISPLAYS_MULTI]
        )
        mock_d.screenshot.return_value = b"png-bytes"
        controller.screenshot(["com.farlightgames.igame.gp"])

        controller.tap(Point(460, 1830))

        mock_d.tap.assert_called_once_with("460", "1830", display_id="2")

    def test_tap_without_prior_resolution_uses_no_display_id(self):
        controller, mock_d = _make_controller([])

        controller.tap(Point(460, 1830))

        mock_d.tap.assert_called_once_with("460", "1830", display_id=None)
