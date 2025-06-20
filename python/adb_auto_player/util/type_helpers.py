"""Helpers for type conversions."""

from typing import Any

import numpy as np


def to_int_if_needed(value: Any) -> int | np.integer:
    """Convert value to int if needed."""
    if isinstance(value, (int | np.integer)):
        return value
    return int(value)
