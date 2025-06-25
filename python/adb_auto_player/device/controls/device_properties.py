from abc import ABC, abstractmethod

from ..device_platform import DevicePlatform


class DeviceProperties(ABC):
    @abstractmethod
    def platform(self) -> DevicePlatform:
        pass

    @abstractmethod
    def resolution(self) -> tuple[int, int]:
        pass
