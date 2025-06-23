"""ADB Auto Player Input Parameter Constrains Module."""

from typing import Literal, TypedDict


class NumberConstraintDict(TypedDict):
    """Number constraint."""

    type: Literal["number"]
    minimum: float | int
    maximum: float | int
    step: float
    default_value: float | int


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
    group_alphabetically: bool


class ImageCheckboxConstraintDict(TypedDict):
    """Image checkbox constraint."""

    type: Literal["imagecheckbox"]
    choices: list[str]
    default_value: list[str]
    image_dir_path: str


class MyCustomRoutineConstraintDict(TypedDict):
    """My Custom Routine constraint."""

    type: Literal["MyCustomRoutine"]
    choices: list[str]
    default_value: list[str]


class TextConstraintDict(TypedDict):
    """Text constraint."""

    type: Literal["text"]
    regex: str
    title: str
    default_value: str


ConstraintType = (
    NumberConstraintDict
    | SelectConstraintDict
    | CheckboxConstraintDict
    | MultiCheckboxConstraintDict
    | ImageCheckboxConstraintDict
    | TextConstraintDict
    | MyCustomRoutineConstraintDict
)
