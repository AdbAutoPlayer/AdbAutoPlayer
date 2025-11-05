from typing import Protocol


class DPad(Protocol):
    """Protocol representing a D-pad (directional pad) interface."""

    def release(self, force: bool = False):
        """Release the D-pad.

        Could be refactored into separate release functions because D-pads can often
        be held in both horizontal and vertical directions.

        Args:
            force: Force release the D-pad. Defaults to False.

        """
        ...

    # ─── Basic 4-Way Movement ─────────────────────────────────────────────
    def up(self, duration: float = 1.0):
        """Move the D-pad up."""
        ...

    def down(self, duration: float = 1.0):
        """Move the D-pad down."""
        ...

    def left(self, duration: float = 1.0):
        """Move the D-pad left."""
        ...

    def right(self, duration: float = 1.0):
        """Move the D-pad right."""
        ...

    # ─── Hold Methods ─────────────────────────────────────────
    def hold_up(self):
        """Hold the D-pad up (no automatic release)."""
        ...

    def hold_down(self):
        """Hold the D-pad down (no automatic release)."""
        ...

    def hold_left(self):
        """Hold the D-pad left (no automatic release)."""
        ...

    def hold_right(self):
        """Hold the D-pad right (no automatic release)."""
        ...


class Stick(Protocol):
    """Protocol representing a joystick stick interface with 8-directional movement."""

    def release(self, force: bool = False):
        """Release the joystick.

        Args:
            force: Force release the stick. Defaults to False.
        """
        ...

    # ─── Basic 4-Way Movement ─────────────────────────────────────────────
    def up(self, duration: float = 1.0, magnitude: float = 1.0):
        """Move the stick up.

        Args:
            duration: how long to hold in seconds
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def down(self, duration: float = 1.0, magnitude: float = 1.0):
        """Move the stick down.

        Args:
            duration: how long to hold in seconds
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def left(self, duration: float = 1.0, magnitude: float = 1.0):
        """Move the stick left.

        Args:
            duration: how long to hold in seconds
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def right(self, duration: float = 1.0, magnitude: float = 1.0):
        """Move the stick right.

        Args:
            duration: how long to hold in seconds
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    # ─── Basic 4-Way Hold Methods ─────────────────────────────────────────
    def hold_up(self, magnitude: float = 1.0):
        """Hold the stick up (no automatic release).

        Args:
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def hold_down(self, magnitude: float = 1.0):
        """Hold the stick down (no automatic release).

        Args:
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def hold_left(self, magnitude: float = 1.0):
        """Hold the stick left (no automatic release).

        Args:
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def hold_right(self, magnitude: float = 1.0):
        """Hold the stick right (no automatic release).

        Args:
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    # ─── Diagonal Movement ────────────────────────────────────────────────
    def up_left(self, duration: float = 1.0, magnitude: float = 1.0):
        """Move the stick up-left.

        Args:
            duration: how long to hold in seconds
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def up_right(self, duration: float = 1.0, magnitude: float = 1.0):
        """Move the stick up-right.

        Args:
            duration: how long to hold in seconds
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def down_left(self, duration: float = 1.0, magnitude: float = 1.0):
        """Move the stick down-left.

        Args:
            duration: how long to hold in seconds
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def down_right(self, duration: float = 1.0, magnitude: float = 1.0):
        """Move the stick down-right.

        Args:
            duration: how long to hold in seconds
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    # ─── Diagonal Hold Methods ───────────────────────────────
    def hold_up_left(self, magnitude: float = 1.0):
        """Hold the stick up-left (no automatic release).

        Args:
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def hold_up_right(self, magnitude: float = 1.0):
        """Hold the stick up-right (no automatic release).

        Args:
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def hold_down_left(self, magnitude: float = 1.0):
        """Hold the stick down-left (no automatic release).

        Args:
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...

    def hold_down_right(self, magnitude: float = 1.0):
        """Hold the stick down-right (no automatic release).

        Args:
            magnitude: how far to move the stick 0 - 1.0 (100%)
        """
        ...
