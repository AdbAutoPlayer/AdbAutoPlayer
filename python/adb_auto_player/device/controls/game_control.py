from abc import ABC, abstractmethod

import numpy as np


class GameControl(ABC):
    @abstractmethod
    def start(self) -> None:
        pass

    @abstractmethod
    def is_running(self) -> bool:
        pass

    @abstractmethod
    def force_stop(self) -> None:
        pass

    @abstractmethod
    def get_screenshot(self) -> np.ndarray:
        pass

    # @abstractmethod
    # def check_requirements(self): pass
