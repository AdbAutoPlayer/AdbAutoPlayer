from abc import ABC, abstractmethod

from adb_auto_player.models.geometry import Coordinates


class DragSwipeControl(ABC):
    @abstractmethod
    def up(self, start: Coordinates, end: Coordinates, duration: float) -> None:
        pass

    @abstractmethod
    def down(self, start: Coordinates, end: Coordinates, duration: float) -> None:
        pass

    @abstractmethod
    def left(self, start: Coordinates, end: Coordinates, duration: float) -> None:
        pass

    @abstractmethod
    def right(self, start: Coordinates, end: Coordinates, duration: float) -> None:
        pass
