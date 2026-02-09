from adb_auto_player.device.adb import AdbController
from adb_auto_player.device.adb.adb_input_device import InputDevice
from adb_auto_player.models.device import DisplayInfo


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

    # ---------- public API ----------

    def tap(self, x: int, y: int) -> None:
        """Fast tap using sendevent."""
        sx = self._scale_x(x)
        sy = self._scale_y(y)

        cmds = [
            # finger down
            f"sendevent "
            f"{self.input_device_file} {self.EV_ABS} {self.ABS_MT_POSITION_X} {sx}",
            f"sendevent "
            f"{self.input_device_file} {self.EV_ABS} {self.ABS_MT_POSITION_Y} {sy}",
            f"sendevent {self.input_device_file} 0 2 0",  # SYN_MT_REPORT
            f"sendevent {self.input_device_file} 0 0 0",  # SYN_REPORT
            # finger up (inferred by silence)
            f"sendevent {self.input_device_file} 0 2 0",  # SYN_MT_REPORT
            f"sendevent {self.input_device_file} 0 0 0",  # SYN_REPORT
        ]

        self._batch(cmds)

    # ---------- scaling ----------

    def _scale_x(self, x: int) -> int:
        return int(x * self.ABS_MAX / self.display_info.resolution.width)

    def _scale_y(self, y: int) -> int:
        return int(y * self.ABS_MAX / self.display_info.resolution.height)

    # ---------- low-level helpers ----------
    @staticmethod
    def _batch(cmds: list[str]) -> None:
        AdbController().d.shell("; ".join(cmds))
