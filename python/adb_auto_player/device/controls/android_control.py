from abc import ABC, abstractmethod

from adb_auto_player.models.geometry import Coordinates

from .drag_swipe_control import DragSwipeControl


class AndroidControl(ABC):
    @abstractmethod
    def tap(self, coordinates: Coordinates) -> None:
        pass

    @abstractmethod
    def hold_tap(self, coordinates: Coordinates, duration: float) -> None:
        pass

    @abstractmethod
    def press_back_button(self) -> None:
        pass

    @property
    @abstractmethod
    def swipe(self) -> DragSwipeControl:
        pass

    # Potential future methods:
    # @abstractmethod
    # def input_text(self, text: str): pass

    # @abstractmethod
    # def keyevent(self, key_code: int): pass  # For volume, home, etc.

    # @abstractmethod
    # def press_home_button(self): pass
