"""ADB Auto Player Input Parameter Constrains Module."""

from typing import Literal, TypedDict


class NumberConstraintDict(TypedDict):
    """Number constraint."""

    type: Literal["number"]
    minimum: int
    maximum: int
    step: float


class SelectConstraintDict(TypedDict):
    """Select constraint."""

    type: Literal["select"]
    choices: list[str]


class CheckboxConstraintDict(TypedDict):
    """Checkbox constraint."""

    type: Literal["checkbox"]


class MultiCheckboxConstraintDict(TypedDict):
    """Multicheckbox constraint."""

    type: Literal["multicheckbox"]
    choices: list[str]


class ImageCheckboxConstraintDict(TypedDict):
    """Image checkbox constraint."""

    type: Literal["imagecheckbox"]
    choices: list[str]


class TextConstraintDict(TypedDict):
    """Text constraint."""

    type: Literal["text"]


ConstraintType = (
    NumberConstraintDict
    | SelectConstraintDict
    | CheckboxConstraintDict
    | MultiCheckboxConstraintDict
    | ImageCheckboxConstraintDict
    | TextConstraintDict
)


def create_number_constraint(
    minimum: int = 1, maximum: int = 999, step: float = 1.0
) -> NumberConstraintDict:
    """Create a number constraint."""
    return NumberConstraintDict(
        type="number",
        minimum=minimum,
        maximum=maximum,
        step=step,
    )


def create_select_constraint(choices: list[str]) -> SelectConstraintDict:
    """Create a select constraint."""
    return SelectConstraintDict(type="select", choices=choices)


def create_checkbox_constraint() -> CheckboxConstraintDict:
    """Create a checkbox constraint."""
    return CheckboxConstraintDict(type="checkbox")


def create_multicheckbox_constraint(choices: list[str]) -> MultiCheckboxConstraintDict:
    """Create a multicheckbox constraint."""
    return MultiCheckboxConstraintDict(type="multicheckbox", choices=choices)


def create_image_checkbox_constraint(choices: list[str]) -> ImageCheckboxConstraintDict:
    """Create an image checkbox constraint."""
    return ImageCheckboxConstraintDict(type="imagecheckbox", choices=choices)


def create_text_constraint() -> TextConstraintDict:
    """Create a text constraint."""
    return TextConstraintDict(type="text")
