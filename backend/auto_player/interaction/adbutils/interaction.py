"""Android Debug Bridge Interaction Module."""

from auto_player.interaction.base import Interaction, InteractionWait
from auto_player.vision.base import Coordinates
from auto_player.connection.base import Connection
from functools import singledispatchmethod
from time import sleep


class AdbInteraction(Interaction, Connection):

    def __init__(self) -> None:
        """Initialize ADB Interactions."""
        super().__init__()

    @singledispatchmethod
    def interact(self, target, wait: InteractionWait) -> None:
        raise NotImplementedError(
            f"Unsupported interaction target type: {type(target)}"
        )

    @interact.register
    def _(self, target: Coordinates, wait: InteractionWait) -> None:
        """Handle tap interactions."""
        sleep(wait.before)
        self.device.click(target.x, target.y)
        sleep(wait.after)

    def _(self, target: tuple[Coordinates, Coordinates], wait: InteractionWait) -> None:
        """Handle swipe and hold interactions."""
        start, end = target
        duration_ms: int = wait.during * 1000

        sleep(wait.before)
        self.device.swipe(start.x, start.y, end.x, end.y, duration_ms)
        sleep(wait.after)

    def tap(self, coordinates: Coordinates, wait: InteractionWait) -> None:
        """Wrap interactions as taps."""
        self.interact(coordinates, wait)
