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


def create_number_constraint(
    default_value: int | float,
    minimum: int | float = 1,
    maximum: int | float = 999,
    step: float = 1.0,
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
    group_alphabetically: bool,
) -> MultiCheckboxConstraintDict:
    """Create a multicheckbox constraint."""
    return MultiCheckboxConstraintDict(
        type="multicheckbox",
        choices=choices,
        default_value=default_value,
        group_alphabetically=group_alphabetically,
    )


def create_image_checkbox_constraint(
    choices: list[str],
    default_value: list[str],
    image_dir_path: str,
) -> ImageCheckboxConstraintDict:
    """Create an image checkbox constraint."""
    return ImageCheckboxConstraintDict(
        type="imagecheckbox",
        choices=choices,
        default_value=default_value,
        image_dir_path=image_dir_path,
    )


def create_my_custom_routine_constraint(
    choices: list[str],
) -> MyCustomRoutineConstraintDict:
    """Create a My Custom Routine constraint."""
    return MyCustomRoutineConstraintDict(
        type="MyCustomRoutine",
        default_value=[],
        choices=choices,
    )


def create_text_constraint(
    default_value: str, regex: str, title: str
) -> TextConstraintDict:
    """Create a text constraint."""
    return TextConstraintDict(
        type="text", regex=regex, title=title, default_value=default_value
    )
