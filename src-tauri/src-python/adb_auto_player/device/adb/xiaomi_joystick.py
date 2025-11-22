import time

from adb_auto_player.device.adb.adb_input_device import InputDevice
from adb_auto_player.models.device import DPad, Stick


class XiaomiJoystick(InputDevice):
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

    @property
    def name(self) -> str:
        """Name of the input device."""
        return "Xiaomi Joystick"

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

    class _Stick(Stick):
        """Stick implementation with 8-directional movement."""

        def __init__(self, parent: "XiaomiJoystick", x_code: int, y_code: int):
            self._parent = parent
            self._x_code = x_code
            self._y_code = y_code
            self.joystick_held: bool = False

        def release(self, force: bool = False):
            if self.joystick_held or force:
                self._parent._release_stick(self._x_code, self._y_code)
                self.joystick_held = False

        def _hold_stick(
            self,
            x_val: int,
            y_val: int,
            magnitude: float,
        ):
            self._parent._hold_stick(
                self._x_code,
                self._y_code,
                int(x_val * magnitude),
                int(y_val * magnitude),
            )
            self.joystick_held = True

        def hold_up(self, magnitude: float = 1.0):
            self._hold_stick(self._parent.CENTER, self._parent.ABS_MIN, magnitude)

        def up(self, duration: float = 1.0, magnitude: float = 1.0):
            self.hold_up(magnitude)
            time.sleep(duration)
            self.release()

        def hold_down(self, magnitude: float = 1.0):
            self._hold_stick(self._parent.CENTER, self._parent.ABS_MAX, magnitude)

        def down(self, duration: float = 1.0, magnitude: float = 1.0):
            self.hold_down(magnitude)
            time.sleep(duration)
            self.release()

        def hold_left(self, magnitude: float = 1.0):
            self._hold_stick(self._parent.ABS_MIN, self._parent.CENTER, magnitude)

        def left(self, duration: float = 1.0, magnitude: float = 1.0):
            self.hold_left(magnitude)
            time.sleep(duration)
            self.release()

        def hold_right(self, magnitude: float = 1.0):
            self._hold_stick(self._parent.ABS_MAX, self._parent.CENTER, magnitude)

        def right(self, duration: float = 1.0, magnitude: float = 1.0):
            self.hold_right(magnitude)
            time.sleep(duration)
            self.release()

        def hold_up_left(self, magnitude: float = 1.0):
            self._hold_stick(self._parent.ABS_MIN, self._parent.ABS_MIN, magnitude)

        def up_left(self, duration: float = 1.0, magnitude: float = 1.0):
            self.hold_up_left(magnitude)
            time.sleep(duration)
            self.release()

        def hold_up_right(self, magnitude: float = 1.0):
            self._hold_stick(self._parent.ABS_MAX, self._parent.ABS_MIN, magnitude)

        def up_right(self, duration: float = 1.0, magnitude: float = 1.0):
            self.hold_up_right(magnitude)
            time.sleep(duration)
            self.release()

        def hold_down_left(self, magnitude: float = 1.0):
            self._hold_stick(self._parent.ABS_MIN, self._parent.ABS_MAX, magnitude)

        def down_left(self, duration: float = 1.0, magnitude: float = 1.0):
            self.hold_down_left(magnitude)
            time.sleep(duration)
            self.release()

        def hold_down_right(self, magnitude: float = 1.0):
            self._hold_stick(self._parent.ABS_MAX, self._parent.ABS_MAX, magnitude)

        def down_right(self, duration: float = 1.0, magnitude: float = 1.0):
            self.hold_down_right(magnitude)
            time.sleep(duration)
            self.release()

    class _DPad(DPad):
        """DPad implementation with 4-directional movement."""

        def __init__(self, parent: "XiaomiJoystick"):
            self._parent = parent
            self._hat_y_held: bool = False
            self._hat_x_held: bool = False

        # ─── Timed Presses ─────────────────────────────────────────────
        def up(self, duration: float = 1.0) -> None:
            self.hold_up()
            time.sleep(duration)
            self.release()

        def down(self, duration: float = 1.0) -> None:
            self.hold_down()
            time.sleep(duration)
            self.release()

        def left(self, duration: float = 1.0) -> None:
            self.hold_left()
            time.sleep(duration)
            self.release()

        def right(self, duration: float = 1.0) -> None:
            self.hold_right()
            time.sleep(duration)
            self.release()

        # ─── Hold Methods ─────────────────────────────────────────────
        def hold_up(self) -> None:
            self._parent._hold_hat(self._parent.ABS_HAT0Y, -1)
            self._hat_y_held = True

        def hold_down(self) -> None:
            self._parent._hold_hat(self._parent.ABS_HAT0Y, 1)
            self._hat_y_held = True

        def hold_left(self) -> None:
            self._parent._hold_hat(self._parent.ABS_HAT0X, -1)
            self._hat_x_held = True

        def hold_right(self) -> None:
            self._parent._hold_hat(self._parent.ABS_HAT0X, 1)
            self._hat_x_held = True

        # ─── Release ─────────────────────────────────────────────
        def release(self, force: bool = True) -> None:
            """Release any held direction on both axes."""
            if self._hat_x_held or force:
                self._parent._release_hat(self._parent.ABS_HAT0X)
                self._hat_x_held = False
            if self._hat_y_held or force:
                self._parent._release_hat(self._parent.ABS_HAT0Y)
                self._hat_y_held = False

    def __init__(self) -> None:
        super().__init__()
        self._left_stick = self._Stick(self, self.ABS_X, self.ABS_Y)
        self._right_stick = self._Stick(self, self.ABS_Z, self.ABS_RZ)
        self._dpad = self._DPad(self)

    def _hold_stick(self, x_code: int, y_code: int, x_val: int, y_val: int) -> None:
        self.sendevent(3, x_code, x_val)
        self.sendevent(3, y_code, y_val)
        self.ev_syn()

    def _release_stick(self, x_code: int, y_code: int) -> None:
        self.sendevent(3, x_code, self.CENTER)
        self.sendevent(3, y_code, self.CENTER)
        self.ev_syn()

    def _hold_hat(self, axis_code: int, value: int) -> None:
        """Hold single D-pad axis."""
        self.sendevent(3, axis_code, value)
        self.ev_syn()

    def _release_hat(self, axis_code: int) -> None:
        """Release D-pad."""
        self.sendevent(3, axis_code, 0)
        self.ev_syn()

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
