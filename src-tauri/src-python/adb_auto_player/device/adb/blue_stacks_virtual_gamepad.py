import time

from adb_auto_player.device.adb.adb_input_device import InputDevice
from adb_auto_player.models.device import DPad, Stick


class BlueStacksVirtualGamepad(InputDevice):
    """BlueStacks Virtual Gamepad implementation.

    shell getevent -p /dev/input/eventX
    name: "BlueStacks Virtual Gamepad"
    events:
        KEY (0001): 0130 0131 0133 0134 0136 0137 0138 0139 013a 013b 013d 013e
        ABS (0003):
            0000 : value 0, min -32768, max 32767, fuzz 16, flat 128, resolution 0
            0001 : value 0, min -32768, max 32767, fuzz 16, flat 128, resolution 0
            0002 : value 0, min -32768, max 32767, fuzz 16, flat 128, resolution 0
            0005 : value 0, min -32768, max 32767, fuzz 16, flat 128, resolution 0
            0009 : value 0, min 0, max 255, fuzz 0, flat 0, resolution 0
            000a : value 0, min 0, max 255, fuzz 0, flat 0, resolution 0
            0010 : value 0, min -1, max 1, fuzz 0, flat 0, resolution 0
            0011 : value 0, min -1, max 1, fuzz 0, flat 0, resolution 0
    """

    @property
    def name(self) -> str:
        """Name of the input device."""
        return "BlueStacks Virtual Gamepad"

    # ─── Axis ranges ─────────────────────────────────────────────
    CENTER = 0
    ABS_MIN = -32768
    ABS_MAX = 32767

    # ─── Sticks ─────────────────────────────────────────────────
    ABS_X = 0  # Left stick X
    ABS_Y = 1  # Left stick Y
    ABS_Z = 2  # Right stick X
    ABS_RZ = 5  # Right stick Y

    # ─── Triggers ───────────────────────────────────────────────
    ABS_LTRIGGER = 9  # Brake
    ABS_RTRIGGER = 10  # Gas

    # ─── D-pad ──────────────────────────────────────────────────
    ABS_HAT0X = 16
    ABS_HAT0Y = 17

    # ────────────────────────────────────────────────────────────
    class _Stick(Stick):
        def __init__(self, parent, x_code, y_code):
            self._parent = parent
            self._x = x_code
            self._y = y_code
            self._held = False

        def _hold(self, x, y, magnitude):
            self._parent._hold_stick(
                self._x,
                self._y,
                int(x * magnitude),
                int(y * magnitude),
            )
            self._held = True

        def release(self, force=False):
            if self._held or force:
                self._parent._release_stick(self._x, self._y)
                self._held = False

        def hold_up(self, magnitude=1.0):
            self._hold(self._parent.CENTER, self._parent.ABS_MIN, magnitude)

        def hold_down(self, magnitude=1.0):
            self._hold(self._parent.CENTER, self._parent.ABS_MAX, magnitude)

        def hold_left(self, magnitude=1.0):
            self._hold(self._parent.ABS_MIN, self._parent.CENTER, magnitude)

        def hold_right(self, magnitude=1.0):
            self._hold(self._parent.ABS_MAX, self._parent.CENTER, magnitude)

        def up(self, duration=1.0, magnitude=1.0):
            self.hold_up(magnitude)
            time.sleep(duration)
            self.release()

        def down(self, duration=1.0, magnitude=1.0):
            self.hold_down(magnitude)
            time.sleep(duration)
            self.release()

        def left(self, duration=1.0, magnitude=1.0):
            self.hold_left(magnitude)
            time.sleep(duration)
            self.release()

        def right(self, duration=1.0, magnitude=1.0):
            self.hold_right(magnitude)
            time.sleep(duration)
            self.release()

    # ────────────────────────────────────────────────────────────
    class _DPad(DPad):
        def __init__(self, parent):
            self._parent = parent
            self._x_held = False
            self._y_held = False

        def hold_up(self):
            self._parent._hold_hat(self._parent.ABS_HAT0Y, -1)
            self._y_held = True

        def hold_down(self):
            self._parent._hold_hat(self._parent.ABS_HAT0Y, 1)
            self._y_held = True

        def hold_left(self):
            self._parent._hold_hat(self._parent.ABS_HAT0X, -1)
            self._x_held = True

        def hold_right(self):
            self._parent._hold_hat(self._parent.ABS_HAT0X, 1)
            self._x_held = True

        def release(self, force=True):
            if self._x_held or force:
                self._parent._release_hat(self._parent.ABS_HAT0X)
                self._x_held = False
            if self._y_held or force:
                self._parent._release_hat(self._parent.ABS_HAT0Y)
                self._y_held = False

        def up(self, duration=1.0):
            self.hold_up()
            time.sleep(duration)
            self.release()

        def down(self, duration=1.0):
            self.hold_down()
            time.sleep(duration)
            self.release()

        def left(self, duration=1.0):
            self.hold_left()
            time.sleep(duration)
            self.release()

        def right(self, duration=1.0):
            self.hold_right()
            time.sleep(duration)
            self.release()

    # ────────────────────────────────────────────────────────────
    def __init__(self):
        super().__init__()
        self._left_stick = self._Stick(self, self.ABS_X, self.ABS_Y)
        self._right_stick = self._Stick(self, self.ABS_Z, self.ABS_RZ)
        self._dpad = self._DPad(self)

    # ─── Low-level helpers ───────────────────────────────────────
    def _hold_stick(self, x_code, y_code, x_val, y_val):
        self.sendevent(3, x_code, x_val)
        self.sendevent(3, y_code, y_val)
        self.ev_syn()

    def _release_stick(self, x_code, y_code):
        self.sendevent(3, x_code, self.CENTER)
        self.sendevent(3, y_code, self.CENTER)
        self.ev_syn()

    def _hold_hat(self, axis, value):
        self.sendevent(3, axis, value)
        self.ev_syn()

    def _release_hat(self, axis):
        self.sendevent(3, axis, 0)
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
