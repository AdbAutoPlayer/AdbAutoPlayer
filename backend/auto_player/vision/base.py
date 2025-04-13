"""Auto Player Vision Base Module."""

from abc import ABC, abstractmethod
from typing import NamedTuple, Generic, TypeVar


T = TypeVar("T")


class Crop(NamedTuple):
    """Percentages of the image to crop from each edge."""

    top: float = 0
    bottom: float = 0
    left: float = 0
    right: float = 0


class Preprocessing(NamedTuple):
    """Image preprocessing options."""

    grayscale: bool
    crop: Crop


class Image(NamedTuple, Generic[T]):
    """Image data for computer vision."""

    image: T
    preprocessing: Preprocessing


class VisionWait(NamedTuple):
    """Wait for image options."""

    appears: int = 0
    disappears: int = 0


class Coordinates(NamedTuple):
    """2D coordinates."""

    x: int
    y: int


class Vision(ABC):
    """Vision abstract base class."""

    @abstractmethod
    def capture(self) -> Image[T]: ...

    @abstractmethod
    def locate(
        self,
        input: Image[T],
        target: Image[T],
        wait: VisionWait,
    ) -> Coordinates | None: ...

    @abstractmethod
    def locate_all(
        self,
        input: Image[T],
        target: Image[T],
        wait: VisionWait,
    ) -> list[Coordinates] | None: ...
