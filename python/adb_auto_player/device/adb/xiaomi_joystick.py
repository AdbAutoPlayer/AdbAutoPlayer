import time

from adb_auto_player.device.adb import AdbController
from adb_auto_player.exceptions import AutoPlayerError
from adb_auto_player.models.device import DPad, Stick


class XiaomiJoystick:
    """Class to interact with Xiaomi Joystick.

    Note:   it is very likely a generic Joystick Class can be made that derives
            necessary data during runtime

    ___
    shell getevent -p /dev/input/eventX
    name:     "Xiaomi Joystick"
    events:
        KEY (0001): 0100  0101  0102  0103  0104  0105  0106  0107
                    0108  0109  0110  0130  0131  0132  0133  0134
                    0135  0136  0137  0138  0139  013a  013b  013c
                    013d  013e  0161  0220  0221  0222  0223
        REL (0002): 0000  0001
        ABS (0003): 0000  : value 0, min -1000000, max 1000000, fuzz 0, flat 0,
                            resolution 0
                    0001  : value 0, min -1000000, max 1000000, fuzz 0, flat 0,
                            resolution 0
                    0002  : value 0, min -1000000, max 1000000, fuzz 0, flat 0,
                            resolution 0
                    0003  : value 0, min 0, max 1, fuzz 0, flat 0, resolution 0
                    0004  : value 0, min 0, max 1, fuzz 0, flat 0, resolution 0
                    0005  : value 0, min -1000000, max 1000000, fuzz 0, flat 0,
                            resolution 0
                    0010  : value 0, min -1, max 1, fuzz 0, flat 0, resolution 0
                    0011  : value 0, min -1, max 1, fuzz 0, flat 0, resolution 0
        FF  (0015): 0050
    ___

    Left Stick (ABS_X, ABS_Y)
    Right Stick (ABS_Z, ABS_RZ)
    Dpad (ABS_HAT0Y, ABS_HAT0X)
    Buttons: BTN_START, BTN_SELECT
        ABXY: BTN_GAMEPAD, BTN_WEST, BTN_NORTH, BTN_EAST
        Triggers: BTN_TL, BTN_TR
        Sticks: BTN_THUMBL, BTN_THUMBR
    Bumpers: ABS_RX (Left), ABS_RY (Right)
    """

    NAME = "Xiaomi Joystick"
    CENTER = 0
    ABS_MIN = -1000000
    ABS_MAX = 1000000

    # Left Stick
    ABS_X = 0
    ABS_Y = 1

    # Right Stick
    ABS_Z = 2
    ABS_RZ = 5

    # D-pad
    ABS_HAT0X = 16
    ABS_HAT0Y = 17

    input_device: str

    class _Stick(Stick):
        """Stick implementation with 8-directional movement."""

        def __init__(self, parent: "XiaomiJoystick", x_code: int, y_code: int):
            self._parent = parent
            self._x_code = x_code
            self._y_code = y_code

        def up(self, duration: float = 1.0) -> None:
            self._parent._move_stick(
                self._x_code,
                self._y_code,
                self._parent.CENTER,
                self._parent.ABS_MIN,
                duration,
            )

        def down(self, duration: float = 1.0) -> None:
            self._parent._move_stick(
                self._x_code,
                self._y_code,
                self._parent.CENTER,
                self._parent.ABS_MAX,
                duration,
            )

        def left(self, duration: float = 1.0) -> None:
            self._parent._move_stick(
                self._x_code,
                self._y_code,
                self._parent.ABS_MIN,
                self._parent.CENTER,
                duration,
            )

        def right(self, duration: float = 1.0) -> None:
            self._parent._move_stick(
                self._x_code,
                self._y_code,
                self._parent.ABS_MAX,
                self._parent.CENTER,
                duration,
            )

        def up_left(self, duration: float = 1.0) -> None:
            self._parent._move_stick(
                self._x_code,
                self._y_code,
                self._parent.ABS_MIN,
                self._parent.ABS_MIN,
                duration,
            )

        def up_right(self, duration: float = 1.0) -> None:
            self._parent._move_stick(
                self._x_code,
                self._y_code,
                self._parent.ABS_MAX,
                self._parent.ABS_MIN,
                duration,
            )

        def down_left(self, duration: float = 1.0) -> None:
            self._parent._move_stick(
                self._x_code,
                self._y_code,
                self._parent.ABS_MIN,
                self._parent.ABS_MAX,
                duration,
            )

        def down_right(self, duration: float = 1.0) -> None:
            self._parent._move_stick(
                self._x_code,
                self._y_code,
                self._parent.ABS_MAX,
                self._parent.ABS_MAX,
                duration,
            )

    class _DPad(DPad):
        """DPad implementation with 4-directional movement."""

        def __init__(self, parent: "XiaomiJoystick"):
            self._parent = parent

        def up(self, duration: float = 1.0) -> None:
            self._parent._move_hat(self._parent.ABS_HAT0Y, -1, duration)

        def down(self, duration: float = 1.0) -> None:
            self._parent._move_hat(self._parent.ABS_HAT0Y, 1, duration)

        def left(self, duration: float = 1.0) -> None:
            self._parent._move_hat(self._parent.ABS_HAT0X, -1, duration)

        def right(self, duration: float = 1.0) -> None:
            self._parent._move_hat(self._parent.ABS_HAT0X, 1, duration)

    def __init__(self) -> None:
        input_device = AdbController().get_input_device(self.NAME)
        if not input_device:
            raise AutoPlayerError(f"Input device '{self.NAME}' cannot be initialized.")
        self.input_device = input_device
        self._left_stick = self._Stick(self, self.ABS_X, self.ABS_Y)
        self._right_stick = self._Stick(self, self.ABS_Z, self.ABS_RZ)
        self._dpad = self._DPad(self)

    def _sendevent(self, ev_type: int, code: int, value: int) -> None:
        AdbController().d.shell(
            f"sendevent {self.input_device} {ev_type} {code} {value}"
        )

    def _ev_syn(self) -> None:
        self._sendevent(0, 0, 0)  # EV_SYN

    def _move_stick(
        self, x_code: int, y_code: int, x_val: int, y_val: int, duration: float
    ) -> None:
        self._sendevent(3, x_code, x_val)
        self._sendevent(3, y_code, y_val)
        self._ev_syn()
        time.sleep(duration)
        # Return to center
        self._sendevent(3, x_code, self.CENTER)
        self._sendevent(3, y_code, self.CENTER)
        self._ev_syn()

    def _move_hat(self, axis_code: int, value: int, duration: float) -> None:
        """Move single D-pad axis."""
        self._sendevent(3, axis_code, value)
        self._ev_syn()
        time.sleep(duration)
        # return to center
        self._sendevent(3, axis_code, 0)
        self._ev_syn()

    # ---------------- Sticks ----------------
    @property
    def left_stick(self) -> Stick:
        """Left Stick."""
        return self._left_stick

    @property
    def l_stick(self) -> Stick:
        """Left Stick."""
        return self._left_stick

    @property
    def right_stick(self) -> Stick:
        """Right Stick."""
        return self._right_stick

    @property
    def r_stick(self) -> Stick:
        """Right Stick."""
        return self._right_stick

    # ---------------- D-pad ----------------
    @property
    def dpad(self) -> DPad:
        """D-pad."""
        return self._dpad
