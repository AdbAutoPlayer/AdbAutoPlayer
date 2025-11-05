from abc import ABC, abstractmethod

from adb_auto_player.device.adb import AdbController
from adb_auto_player.exceptions import AutoPlayerError


class InputDevice(ABC):
    """Abstract class for Android Input Device."""

    EV_SYN = 0x00

    _input_device: str | None = None

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the input device."""
        pass

    @property
    def input_device_file(self) -> str:
        """Input device file."""
        if self._input_device:
            return self._input_device
        self._input_device = AdbController().get_input_device(self.name)
        if not self._input_device:
            raise AutoPlayerError(f"Input device '{self.name}' cannot be initialized.")
        return self._input_device

    def sendevent(self, ev_type: int, code: int, value: int) -> None:
        """ADB sendevent."""
        AdbController().d.shell(
            f"sendevent {self.input_device_file} {ev_type} {code} {value}"
        )

    def ev_syn(self) -> None:
        """EV_SYN."""
        self.sendevent(self.EV_SYN, 0, 0)
