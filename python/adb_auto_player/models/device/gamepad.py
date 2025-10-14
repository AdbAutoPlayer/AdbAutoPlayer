from typing import Protocol


class DPad(Protocol):
    """Protocol representing a D-pad (directional pad) interface."""

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


class Stick(DPad):
    """Protocol representing a joystick stick interface with 8-directional movement."""

    def up_left(self, duration: float = 1.0):
        """Move the stick diagonally up-left."""
        ...

    def up_right(self, duration: float = 1.0):
        """Move the stick diagonally up-right."""
        ...

    def down_left(self, duration: float = 1.0):
        """Move the stick diagonally down-left."""
        ...

    def down_right(self, duration: float = 1.0):
        """Move the stick diagonally down-right."""
        ...
