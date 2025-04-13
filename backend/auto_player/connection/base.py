"""Auto Player Connection Base Module."""

from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T")


class Connection(ABC):

    def __init__(self) -> None:
        self._device: T | None = None

    @property
    def device(self) -> T:
        return self._device

    @device.setter
    def device(self, device: T) -> None:
        self._device = device

    @abstractmethod
    def connect(self, device: str) -> None: ...
