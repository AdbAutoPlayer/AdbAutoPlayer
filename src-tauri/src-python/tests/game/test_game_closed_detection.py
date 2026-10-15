"""Tests for detecting that the emulator closed the game mid-task.

Regression tests for: MuMuPlayer can close the game on its own while ADB keeps
running. Task loops kept matching templates against the home launcher instead
of noticing the game was gone and restarting it.
"""

from unittest.mock import MagicMock, patch

import pytest
from adb_auto_player.device.adb.adb_controller import AdbController
from adb_auto_player.exceptions import (
    GameNotRunningOrFrozenError,
    GameStartError,
    GenericAdbUnrecoverableError,
)
from adb_auto_player.game import Game, _screenshot_mixin
from pydantic import BaseModel

_GAME = "com.farlightgames.igame.gp"
_LAUNCHER = "app.lawnchair"

# Real parsed output of the `get_running_app` pipeline on MuMuPlayer Android 15
# with the game open on display 2 and the launcher resumed on display 0.
_RESUMED_MULTI_DISPLAY = f"{_GAME}\n{_LAUNCHER}\n{_GAME}\n"

_PM_LIST_PACKAGES = f"""package:{_GAME}
package:{_GAME}.vn
"""


class _StubGame(Game):
    def __init__(self) -> None:
        super().__init__()
        self.package_name_prefixes = [_GAME]
        # Typed MagicMock handle for assertions: `_device` is declared as
        # `AdbController | None`, so the type checker hides the mock API
        self.device_mock = MagicMock()
        self._device = self.device_mock

    @property
    def settings(self) -> BaseModel:
        return BaseModel()


def _controller(shell_output: str) -> AdbController:
    controller = AdbController.__new__(AdbController)
    controller.d = MagicMock()
    controller.d.shell.return_value = shell_output
    return controller


class TestGetResumedApps:
    def test_returns_unique_packages_from_every_display(self) -> None:
        controller = _controller(_RESUMED_MULTI_DISPLAY)
        assert controller.get_resumed_apps() == [_GAME, _LAUNCHER]

    def test_empty_output_returns_empty_list(self) -> None:
        assert _controller("\n").get_resumed_apps() == []


class TestIsGameRunning:
    def test_game_on_non_first_display_is_running(self) -> None:
        game = _StubGame()
        game.device_mock.get_resumed_apps.return_value = [_LAUNCHER, _GAME]
        assert game.is_game_running()
        assert game._target_package_name == _GAME

    def test_only_launcher_resumed_is_not_running(self) -> None:
        game = _StubGame()
        game._target_package_name = _GAME
        game.device_mock.get_resumed_apps.return_value = [_LAUNCHER]
        assert not game.is_game_running()


class TestRaiseIfGameClosed:
    def test_raises_when_game_closed(self) -> None:
        game = _StubGame()
        game._target_package_name = _GAME
        game.device_mock.get_resumed_apps.return_value = [_LAUNCHER]
        with pytest.raises(GameNotRunningOrFrozenError):
            game._raise_if_game_closed()

    def test_skipped_before_game_was_seen_running(self) -> None:
        game = _StubGame()
        game._raise_if_game_closed()
        game.device_mock.get_resumed_apps.assert_not_called()

    def test_checks_at_most_once_per_interval(self) -> None:
        game = _StubGame()
        game._target_package_name = _GAME
        game.device_mock.get_resumed_apps.return_value = [_GAME]
        interval = _screenshot_mixin._GAME_RUNNING_CHECK_INTERVAL_SECONDS
        with patch.object(
            _screenshot_mixin, "monotonic", side_effect=[100.0, 101.0, 100 + interval]
        ):
            game._raise_if_game_closed()
            game._raise_if_game_closed()
            game._raise_if_game_closed()
        assert game.device_mock.get_resumed_apps.call_count == 2

    def test_get_screenshot_raises_when_game_closed(self) -> None:
        game = _StubGame()
        game._target_package_name = _GAME
        game.device_mock.get_resumed_apps.return_value = [_LAUNCHER]
        with pytest.raises(GameNotRunningOrFrozenError):
            game.get_screenshot()
        game.device_mock.screenshot.assert_not_called()

    def test_failed_screenshot_after_game_closed_reports_closure(self) -> None:
        """Regression found live on MuMuPlayer.

        Closing the game removes its virtual display, so `screencap -d` fails
        before the periodic check runs.
        """
        game = _StubGame()
        game._target_package_name = _GAME
        game.device_mock.get_resumed_apps.side_effect = [[_GAME], [_LAUNCHER]]
        game.device_mock.screenshot.side_effect = OSError("Capturing failed.")
        with (
            patch.object(_screenshot_mixin, "sleep"),
            pytest.raises(GameNotRunningOrFrozenError),
        ):
            game.get_screenshot()

    def test_failed_screenshot_with_game_running_is_adb_error(self) -> None:
        game = _StubGame()
        game._target_package_name = _GAME
        game.device_mock.get_resumed_apps.return_value = [_GAME]
        game.device_mock.screenshot.side_effect = OSError("Capturing failed.")
        with (
            patch.object(_screenshot_mixin, "sleep"),
            pytest.raises(GenericAdbUnrecoverableError),
        ):
            game.get_screenshot()


class TestGetInstalledPackages:
    def test_parses_pm_list_packages(self) -> None:
        controller = _controller(_PM_LIST_PACKAGES)
        assert controller.get_installed_packages(_GAME) == [_GAME, f"{_GAME}.vn"]

    def test_nothing_installed(self) -> None:
        assert _controller("").get_installed_packages(_GAME) == []


class TestStartGameWhenAlreadyClosed:
    """Regression: a game already closed when the task starts was never launched.

    `_target_package_name` is only learned by seeing the game running, so
    `start_game()` silently did nothing and `open_eyes()` failed with
    "Game could not be started".
    """

    def test_launches_installed_package(self) -> None:
        game = _StubGame()
        game.device_mock.get_installed_packages.return_value = [_GAME]
        game.start_game()
        game.device_mock.start_game.assert_called_once_with(_GAME)
        assert game._target_package_name == _GAME

    def test_prefers_exact_package_over_variant(self) -> None:
        game = _StubGame()
        game.device_mock.get_installed_packages.return_value = [f"{_GAME}.vn", _GAME]
        game.start_game()
        game.device_mock.start_game.assert_called_once_with(_GAME)

    def test_uses_variant_when_only_one_installed(self) -> None:
        game = _StubGame()
        game.device_mock.get_installed_packages.return_value = [f"{_GAME}.vn"]
        game.start_game()
        game.device_mock.start_game.assert_called_once_with(f"{_GAME}.vn")

    def test_not_installed_raises(self) -> None:
        game = _StubGame()
        game.device_mock.get_installed_packages.return_value = []
        with pytest.raises(GameStartError):
            game.start_game()
        game.device_mock.start_game.assert_not_called()

    def test_open_eyes_starts_closed_game(self) -> None:
        game = _StubGame()
        game.device_mock.get_resumed_apps.side_effect = [
            [_LAUNCHER],
            [_LAUNCHER, _GAME],
        ]
        game.device_mock.get_installed_packages.return_value = [_GAME]
        with (
            patch.object(_StubGame, "_set_device_resolution"),
            patch.object(_StubGame, "_check_requirements"),
            patch.object(_StubGame, "_start_device_streaming"),
            patch.object(_StubGame, "_check_screenshot_matches_display_resolution"),
        ):
            game.open_eyes()
        game.device_mock.start_game.assert_called_once_with(_GAME)
        # The game's display only exists once it runs: target it afterwards.
        calls = [c[0] for c in game.device_mock.mock_calls]
        assert calls.index("start_game") < calls.index("reset_display_targeting")
        assert calls.index("reset_display_targeting") < calls.index(
            "resolve_display_targeting"
        )
