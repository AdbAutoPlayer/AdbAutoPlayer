"""Input control mixin — tap, hold, swipe operations."""

import logging
import threading
from dataclasses import dataclass
from enum import StrEnum, auto
from time import sleep

from adb_auto_player.models.geometry import Coordinates, Point

from ._base import _GameBase


class _SwipeDirection(StrEnum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()

    @property
    def is_vertical(self) -> bool:
        """Return True if the direction is vertical (UP or DOWN)."""
        return self in {_SwipeDirection.UP, _SwipeDirection.DOWN}

    @property
    def is_increasing(self) -> bool:
        """Return True if the coordinate increases in the direction (DOWN or RIGHT)."""
        return self in {_SwipeDirection.DOWN, _SwipeDirection.RIGHT}


@dataclass
class _SwipeParams:
    direction: _SwipeDirection
    x: int | None = None
    y: int | None = None
    start: int | None = None
    end: int | None = None
    duration: float = 1.0


class _InputMixin(_GameBase):
    """Mixin providing all user-input operations (tap, hold, swipe)."""

    def tap(
        self,
        coordinates: Coordinates,
        scale: bool = False,  # TODO remove later
        blocking: bool = True,
        # Assuming 30 FPS, 1 Tap per Frame
        non_blocking_sleep_duration: float | None = 1 / 30,
        log_message: str | None = None,
        log: bool = True,
    ) -> None:
        """Tap the screen on the given point.

        Args:
            coordinates (Coordinates): Point to click on.
            scale (bool, optional): Deprecated — does nothing.
            blocking (bool, optional): Whether to block until ADB confirms the tap.
            non_blocking_sleep_duration (float, optional): Sleep time in seconds for
                non-blocking taps, needed to not DoS the ADB server.
            log_message (str | None, optional): Custom log message; default if None.
            log (bool, optional): Log the tap command.
        """
        if log:
            log_message = (log_message or "Tapped") + f": {coordinates}"
        else:
            log_message = None

        if blocking:
            self._click(coordinates, log_message)
        else:
            thread = threading.Thread(
                target=self._click,
                args=(coordinates, log_message),
                daemon=True,
            )
            thread.start()
            if non_blocking_sleep_duration is not None:
                sleep(non_blocking_sleep_duration)

    def _click(
        self,
        coordinates: Coordinates,
        log_message: str | None = None,
    ) -> None:
        """Internal click method — logging should be handled by the caller."""
        self.device.tap(coordinates)
        if log_message is not None:
            logging.debug(log_message)

    def press_back_button(self) -> None:
        """Press the device back button."""
        self.device.press_back_button()

    def swipe_down(
        self,
        x: int | None = None,
        sy: int | None = None,
        ey: int | None = None,
        duration: float = 1.0,
    ) -> None:
        """Perform a vertical swipe from top to bottom.

        Args:
            x (int, optional): X-coordinate. Defaults to horizontal center.
            sy (int, optional): Start Y. Defaults to top edge (0).
            ey (int, optional): End Y. Defaults to bottom edge.
            duration (float, optional): Duration in seconds. Defaults to 1.0.
        """
        self._swipe_direction(
            _SwipeParams(_SwipeDirection.DOWN, x=x, start=sy, end=ey, duration=duration)
        )

    def swipe_up(
        self,
        x: int | None = None,
        sy: int | None = None,
        ey: int | None = None,
        duration: float = 1.0,
    ) -> None:
        """Perform a vertical swipe from bottom to top.

        Args:
            x (int, optional): X-coordinate. Defaults to horizontal center.
            sy (int, optional): Start Y. Defaults to bottom edge.
            ey (int, optional): End Y. Defaults to top edge (0).
            duration (float, optional): Duration in seconds. Defaults to 1.0.
        """
        self._swipe_direction(
            _SwipeParams(_SwipeDirection.UP, x=x, start=sy, end=ey, duration=duration)
        )

    def swipe_right(
        self,
        y: int | None = None,
        sx: int | None = None,
        ex: int | None = None,
        duration: float = 1.0,
    ) -> None:
        """Perform a horizontal swipe from left to right.

        Args:
            y (int, optional): Y-coordinate. Defaults to vertical center.
            sx (int, optional): Start X. Defaults to left edge (0).
            ex (int, optional): End X. Defaults to right edge.
            duration (float, optional): Duration in seconds. Defaults to 1.0.
        """
        self._swipe_direction(
            _SwipeParams(
                _SwipeDirection.RIGHT, y=y, start=sx, end=ex, duration=duration
            )
        )

    def swipe_left(
        self,
        y: int | None = None,
        sx: int | None = None,
        ex: int | None = None,
        duration: float = 1.0,
    ) -> None:
        """Perform a horizontal swipe from right to left.

        Args:
            y (int, optional): Y-coordinate. Defaults to vertical center.
            sx (int, optional): Start X. Defaults to right edge.
            ex (int, optional): End X. Defaults to left edge (0).
            duration (float, optional): Duration in seconds. Defaults to 1.0.
        """
        self._swipe_direction(
            _SwipeParams(_SwipeDirection.LEFT, y=y, start=sx, end=ex, duration=duration)
        )

    def _swipe_direction(self, params: _SwipeParams) -> None:
        rx, ry = self.display_info.dimensions
        direction = params.direction

        coord = params.x if direction.is_vertical else params.y
        coord = (
            (rx // 2 if direction.is_vertical else ry // 2) if coord is None else coord
        )

        start = params.start or (
            0 if direction.is_increasing else (ry if direction.is_vertical else rx)
        )
        end = params.end or (
            (ry if direction.is_vertical else rx) if direction.is_increasing else 0
        )

        if (direction.is_increasing and start >= end) or (
            not direction.is_increasing and start <= end
        ):
            raise ValueError(
                f"Start must be {'less' if direction.is_increasing else 'greater'} "
                f"than end to swipe {direction.value}."
            )

        sx, sy, ex, ey = (
            (coord, start, coord, end)
            if direction.is_vertical
            else (start, coord, end, coord)
        )

        logging.debug(f"swipe_{direction} - from ({sx}, {sy}) to ({ex}, {ey})")
        self.device.swipe(
            Point(sx, sy),
            Point(ex, ey),
            duration=params.duration,
        )

    def hold(
        self,
        coordinates: Coordinates,
        duration: float = 3.0,
        blocking: bool = True,
        log: bool = True,
    ) -> threading.Thread | None:
        """Hold a point on the screen.

        Args:
            coordinates (Coordinates): Point on the screen.
            duration (float, optional): Hold duration. Defaults to 3.0.
            blocking (bool, optional): Whether the call blocks.
            log (bool, optional): Log the hold command.
        """
        point = Point(coordinates.x, coordinates.y)

        if log:
            logging.debug(
                f"hold: ({coordinates.x}, {coordinates.y}) for {duration} seconds"
            )

        if blocking:
            self.device.hold(coordinates=point, duration=duration)
            return None

        thread = threading.Thread(
            target=self.device.hold,
            kwargs={"coordinates": point, "duration": duration},
            daemon=True,
        )
        thread.start()
        return thread
