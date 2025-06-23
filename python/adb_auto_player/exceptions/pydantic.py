"""Pydantic config validation errors."""


class InvalidBoundaryError(ValueError):
    """Raise when default value is outside min-max bounds.

    This means you have to set ge and/or le in the Pydantic Field schema.
    """

    pass


class MissingBoundaryValueError(ValueError):
    """Raised when a number config is missing its min or max boundary.

    This means you have to set ge or gt and le or lt in the Pydantic Field schema.
    """

    pass


class MissingDefaultValueError(ValueError):
    """Raised when a config field is missing a default value."""

    pass


class InvalidDefaultValueError(ValueError):
    """Raised when a config field default value is invalid."""

    pass


class RegexMissingTitleError(ValueError):
    """Raised when a config field defines regex without title."""

    pass
