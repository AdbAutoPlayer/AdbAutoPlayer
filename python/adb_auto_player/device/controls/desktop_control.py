from abc import ABC, abstractmethod

from .keyboard_control import KeyboardControl
from .mouse_control import MouseControl


class DesktopControl(ABC):
    @property
    @abstractmethod
    def mouse(self) -> MouseControl:
        pass

    @property
    @abstractmethod
    def keyboard(self) -> KeyboardControl:
        pass
