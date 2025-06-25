from abc import ABC, abstractmethod

from adb_auto_player.models.geometry import Coordinates

from .drag_swipe_control import DragSwipeControl


class MouseControl(ABC):
    @abstractmethod
    def left_click(self, coordinates: Coordinates):
        pass

    @abstractmethod
    def hold_left_click(self, coordinates: Coordinates, duration: float):
        pass

    @abstractmethod
    def right_click(self, coordinates: Coordinates):
        pass

    @abstractmethod
    def hold_right_click(self, coordinates: Coordinates, duration: float):
        pass

    @abstractmethod
    def scroll_wheel_up(self, coordinates: Coordinates, duration: float):
        pass

    @abstractmethod
    def scroll_wheel_down(self, coordinates: Coordinates, duration: float):
        pass

    @abstractmethod
    def scroll_wheel_click(self, coordinates: Coordinates):
        pass

    @abstractmethod
    def hold_scroll_wheel(self, coordinates: Coordinates, duration: float):
        pass

    @abstractmethod
    @property
    def drag(self) -> DragSwipeControl:
        pass
