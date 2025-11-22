"""Helpers for type conversions."""

from typing import Any

import numpy as np


class TypeHelper:
    """Type and Type conversion related helpers."""

    @staticmethod
    def to_int_if_needed(value: Any) -> int | np.integer:
        """Convert value to int if needed."""
        if isinstance(value, (int | np.integer)):
            return value
        return int(value)
