from abc import ABC, abstractmethod

import numpy as np
from adb_auto_player.device.controls import (
    AndroidControl,
    DesktopControl,
    DeviceProperties,
    GameControl,
)
from adb_auto_player.models.geometry import Coordinates


class DeviceInterface(ABC):
    @property
    @abstractmethod
    def properties(self) -> DeviceProperties:
        pass

    @property
    @abstractmethod
    def game(self) -> GameControl:
        pass

    @property
    @abstractmethod
    def android(self) -> AndroidControl:
        pass

    @property
    @abstractmethod
    def desktop(self) -> DesktopControl:
        pass

    # Aliases
    def get_screenshot(self) -> np.ndarray:
        return self.game.get_screenshot()

    def tap(self, coordinates: Coordinates) -> None:
        self.android.tap(coordinates)

    def click(self, coordinates: Coordinates) -> None:
        self.desktop.mouse.left_click(coordinates)

    def press_back_button(self) -> None:
        self.android.press_back_button()
