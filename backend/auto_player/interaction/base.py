"""Auto Player Interaction Base Module."""

from abc import ABC, abstractmethod
from auto_player.vision.base import Coordinates
from functools import singledispatchmethod
from typing import NamedTuple


class InteractionWait(NamedTuple):
    """Wait for interaction options."""

    before: int = 0
    during: int = 0
    after: int = 0


class Interaction(ABC):
    """Interaction abstract base class."""

    @singledispatchmethod
    @abstractmethod
    def interact(self, target, wait: InteractionWait) -> None: ...

    @interact.register
    @abstractmethod
    def _(self, target: Coordinates, wait: InteractionWait) -> None: ...

    @interact.register
    @abstractmethod
    def _(
        self,
        target: tuple[Coordinates, Coordinates],
        wait: InteractionWait,
    ) -> None: ...
