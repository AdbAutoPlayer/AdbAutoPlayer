"""Game lifecycle mixin — startup, shutdown, and running-state checks."""

import logging
from time import perf_counter

from adb_auto_player.exceptions import GameNotRunningOrFrozenError
from adb_auto_player.models.geometry import PointOutsideDisplay

from ._base import _GameBase


class _LifecycleMixin(_GameBase):
    """Mixin that manages the game process lifecycle."""

    def open_eyes(self, device_streaming: bool = True) -> None:
        """Prepare the bot for operation.

        Validates device resolution, starts the stream (if requested), and ensures
        the game is running.

        Args:
            device_streaming (bool, optional): Whether to start the H264 stream.
        """
        self._set_device_resolution()
        self._check_requirements()
        self._start_device_streaming(device_streaming=device_streaming)
        self._check_screenshot_matches_display_resolution(device_streaming_check=False)

        if self.is_game_running():
            return

        logging.warning("Game is not running, trying to start the game.")
        self.start_game()
        if not self.is_game_running():
            raise GameNotRunningOrFrozenError("Game could not be started, exiting...")

    def force_stop_game(self) -> None:
        """Force-stop the game process."""
        if not self._target_package_name:
            return
        self.device.stop_game(self._target_package_name)

    def is_game_running(self) -> bool:
        """Return True if the game process is currently active."""
        if app := self.device.get_running_app():
            if self._target_package_name:
                return app == self._target_package_name
            if any(pn in app for pn in self.package_name_prefixes):
                self._target_package_name = app
                return True
        return False

    def start_game(self) -> None:
        """Launch the game via ADB.

        Raises:
            GameStartError: Game cannot be started.
        """
        if not self._target_package_name:
            return
        self.device.start_game(self._target_package_name)

    def restart_game(self) -> None:
        """Force-stop then relaunch the game."""
        self.force_stop_game()
        self.start_game()

    def assert_frame_and_input_delay_below_threshold(
        self,
        max_frame_delay: int = 10,
        max_input_delay: int = 80,
    ) -> None:
        """Assert frame and input lag are below acceptable thresholds.

        Intended for bots that need fast input/reaction time.

        Args:
            max_frame_delay(int, optional): Maximum frame delay in milliseconds.
            max_input_delay(int, optional): Maximum input delay in milliseconds.
        """
        start_time = perf_counter()
        _ = self.get_screenshot()
        total_time = (perf_counter() - start_time) * 1000
        if total_time > max_frame_delay:
            logging.warning(
                f"Screenshot/Frame delay: {int(total_time)} ms above max frame delay: "
                f"{max_frame_delay} ms. Performance may be poor."
            )
        else:
            logging.info(f"Screenshot/Frame delay: {int(total_time)} ms")

        total_time = 0.0
        iterations = 10
        for _ in range(iterations):
            start_time = perf_counter()
            self.tap(PointOutsideDisplay(), log=False, non_blocking_sleep_duration=None)
            total_time += (perf_counter() - start_time) * 1000
        average_time = total_time / iterations
        if average_time > max_input_delay:
            logging.warning(
                f"Average input delay: {int(average_time)} ms above max input delay: "
                f"{max_input_delay} ms. Performance may be poor."
            )
        else:
            logging.info(f"Average input delay: {int(average_time)} ms")
