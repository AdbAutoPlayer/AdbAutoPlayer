import typing

from adb_auto_player.device.adb import AdbController
from adb_auto_player.device.adb.adb_input_device import InputDevice
from adb_auto_player.models.device import DisplayInfo
from adb_auto_player.models.geometry import Coordinates


class BlueStacksVirtualTouch(InputDevice):
    """BlueStacks Virtual Touch implementation.

    shell getevent -p /dev/input/eventX
    name:     "BlueStacks Virtual Touch"
    events:
        ABS (0003): 0035  : value 0, min 0, max 32767, fuzz 0, flat 0, resolution 0
                    0036  : value 0, min 0, max 32767, fuzz 0, flat 0, resolution 0
    """

    @property
    def name(self) -> str:
        """Name of the input device."""
        return "BlueStacks Virtual Touch"

    def __init__(self, display_info: DisplayInfo) -> None:
        self.display_info = display_info

    # Event types
    EV_ABS = 0x0003

    # Absolute axis range
    ABS_MIN = 0
    ABS_MAX = 32767

    # Multi-touch axes
    ABS_MT_POSITION_X = 0x0035
    ABS_MT_POSITION_Y = 0x0036

    RELEASE_FRAME_CMDS: typing.ClassVar = [
        "0 2 0",  # SYN_MT_REPORT
        "0 0 0",  # SYN_REPORT
    ]

    # ---------- public API ----------

    def hold(self, coordinates: Coordinates) -> None:
        """Finger down and hold."""
        sx = self._scale_x(coordinates.x)
        sy = self._scale_y(coordinates.y)

        cmds = [
            f"{self.EV_ABS} {self.ABS_MT_POSITION_X} {sx}",
            f"{self.EV_ABS} {self.ABS_MT_POSITION_Y} {sy}",
            "0 2 0",  # SYN_MT_REPORT
            "0 0 0",  # SYN_REPORT
        ]

        self._batch(cmds)

    def release(self) -> None:
        """Release the currently held finger."""
        self._batch(self.RELEASE_FRAME_CMDS)

    def tap(self, coordinates: Coordinates) -> None:
        """Fast tap using a single batch command."""
        sx = self._scale_x(coordinates.x)
        sy = self._scale_y(coordinates.y)

        cmds = [
            f"{self.EV_ABS} {self.ABS_MT_POSITION_X} {sx}",
            f"{self.EV_ABS} {self.ABS_MT_POSITION_Y} {sy}",
            "0 2 0",  # SYN_MT_REPORT
            "0 0 0",  # SYN_REPORT
            *self.RELEASE_FRAME_CMDS,  # finger up
        ]

        self._batch(cmds)

    # ---------- scaling ----------

    def _scale_x(self, x: int) -> int:
        return int(x * self.ABS_MAX / self.display_info.resolution.width)

    def _scale_y(self, y: int) -> int:
        return int(y * self.ABS_MAX / self.display_info.resolution.height)

    # ---------- low-level helpers ----------
    def _batch(self, cmds: list[str]) -> None:
        full_cmds = [f"sendevent {self.input_device_file} {cmd}" for cmd in cmds]
        AdbController().d.shell("; ".join(full_cmds))
