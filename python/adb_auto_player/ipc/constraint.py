"""ADB Auto Player Input Parameter Constrains Module."""

from typing import Literal, TypedDict


class NumberConstraintDict(TypedDict):
    """Number constraint."""

    type: Literal["number"]
    minimum: int
    maximum: int
    step: float
    default_value: int


class SelectConstraintDict(TypedDict):
    """Select constraint."""

    type: Literal["select"]
    choices: list[str]
    default_value: str


class CheckboxConstraintDict(TypedDict):
    """Checkbox constraint."""

    type: Literal["checkbox"]
    default_value: bool


class MultiCheckboxConstraintDict(TypedDict):
    """Multicheckbox constraint."""

    type: Literal["multicheckbox"]
    choices: list[str]
    default_value: list[str]


class ImageCheckboxConstraintDict(TypedDict):
    """Image checkbox constraint."""

    type: Literal["imagecheckbox"]
    choices: list[str]
    default_value: list[str]


class TextConstraintDict(TypedDict):
    """Text constraint."""

    type: Literal["text"]
    regex: str
    default_value: str


ConstraintType = (
    NumberConstraintDict
    | SelectConstraintDict
    | CheckboxConstraintDict
    | MultiCheckboxConstraintDict
    | ImageCheckboxConstraintDict
    | TextConstraintDict
)


def create_number_constraint(
    default_value: int, minimum: int = 1, maximum: int = 999, step: float = 1.0
) -> NumberConstraintDict:
    """Create a number constraint."""
    return NumberConstraintDict(
        type="number",
        minimum=minimum,
        maximum=maximum,
        step=step,
        default_value=default_value,
    )


def create_select_constraint(
    choices: list[str], default_value: str
) -> SelectConstraintDict:
    """Create a select constraint."""
    return SelectConstraintDict(
        type="select",
        choices=choices,
        default_value=default_value,
    )


def create_checkbox_constraint(default_value: bool) -> CheckboxConstraintDict:
    """Create a checkbox constraint."""
    return CheckboxConstraintDict(
        type="checkbox",
        default_value=default_value,
    )


def create_multicheckbox_constraint(
    choices: list[str],
    default_value: list[str],
) -> MultiCheckboxConstraintDict:
    """Create a multicheckbox constraint."""
    return MultiCheckboxConstraintDict(
        type="multicheckbox",
        choices=choices,
        default_value=default_value,
    )


def create_image_checkbox_constraint(
    choices: list[str],
    default_value: list[str],
) -> ImageCheckboxConstraintDict:
    """Create an image checkbox constraint."""
    return ImageCheckboxConstraintDict(
        type="imagecheckbox",
        choices=choices,
        default_value=default_value,
    )


def create_text_constraint(default_value: str) -> TextConstraintDict:
    """Create a text constraint."""
    return TextConstraintDict(type="text", regex="", default_value=default_value)
