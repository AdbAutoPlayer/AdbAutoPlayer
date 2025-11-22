"""CustomRoutineEntry."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CustomRoutineEntry:
    """Represents a registered custom routine choice entry.

    Attributes:
        func (Callable): The function implementing the custom routine.
        kwargs (dict[str, Any]): Optional default keyword arguments to pass
            when invoking the function.
    """

    func: Callable
    kwargs: dict[str, Any] = field(default_factory=dict)
