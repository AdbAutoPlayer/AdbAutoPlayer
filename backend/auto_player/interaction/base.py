"""Auto Player Interaction Base Module."""

from abc import ABC, abstractmethod
from functools import singledispatchmethod
from typing import Any

from auto_player.connection.base import Connection
from auto_player.interaction.models import (
    Coordinates,
    InteractionWait,
    KeyEvent,
)


class Interaction(ABC):
    """Interaction abstract base class.

    This class defines a generic interface for simulating user input interactions.
    It uses a singledispatchmethod to handle different types of interaction targets.
    """

    def __init__(self, connection: Connection) -> None:
        """Initializes the Interaction service with a connection instance.

        Args:
            connection: An instance of a Connection subclass to communicate with the device/system.
        """
        self._connection = connection

    @singledispatchmethod
    @abstractmethod
    def interact(self, target: Any, wait: InteractionWait | None = None, **kwargs: Any) -> None:
        """Performs an interaction based on the type of 'target' provided.

        Concrete implementations should register handlers for specific target types.
        This base dispatcher raises a TypeError for unhandled types.

        Args:
            target: The object defining the interaction (e.g., Coordinates, tuple of Coordinates, str for text, KeyEvent).
            wait: Optional InteractionWait object specifying delays.
            **kwargs: Additional keyword arguments for specific interaction types (e.g., duration_ms, hold_duration_ms).

        Raises:
            TypeError: If no handler is registered for the type of 'target'.
        """
        raise TypeError(f"No interaction handler registered for type {type(target)}")

    @interact.register
    @abstractmethod
    def _handle_coordinates_interaction(
        self, target: Coordinates, wait: InteractionWait | None = None, **kwargs: Any
    ) -> None:
        """Handles interaction at a single point (e.g., tap, click).

        Args:
            target: The Coordinates for the interaction.
            wait: Optional InteractionWait object.
            **kwargs: May include 'hold_duration_ms' for a long press/click.
        """
        ...

    @interact.register
    @abstractmethod
    def _handle_coordinate_pair_interaction(
        self,
        target: tuple[Coordinates, Coordinates],
        wait: InteractionWait | None = None,
        *,
        duration_ms: int,
        **kwargs: Any,
    ) -> None:
        """Handles interaction between two points (e.g., swipe, drag).

        Args:
            target: A tuple containing start and end Coordinates.
            wait: Optional InteractionWait object.
            duration_ms: The duration of the interaction in milliseconds (required).
            **kwargs: Additional arguments for the specific interaction.
        """
        ...

    @interact.register
    @abstractmethod
    def _handle_text_interaction(
        self, target: str, wait: InteractionWait | None = None, **kwargs: Any
    ) -> None:
        """Handles text input interaction.

        Args:
            target: The string of text to input.
            wait: Optional InteractionWait object.
            **kwargs: Additional arguments for the specific interaction.
        """
        ...

    @interact.register
    @abstractmethod
    def _handle_key_event_interaction(
        self, target: KeyEvent, wait: InteractionWait | None = None, **kwargs: Any
    ) -> None:
        """Handles key event interaction.

        Args:
            target: The KeyEvent object defining the key to press.
            wait: Optional InteractionWait object.
            **kwargs: Additional arguments for the specific interaction.
        """
        ...
