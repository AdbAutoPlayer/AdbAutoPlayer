from typing import TypedDict, Literal, Union


class NumberConstraintDict(TypedDict):
    type: Literal["number"]
    minimum: int
    maximum: int
    step: float


class SelectConstraintDict(TypedDict):
    type: Literal["select"]
    choices: list[str]


class CheckboxConstraintDict(TypedDict):
    type: Literal["checkbox"]


class MultiCheckboxConstraintDict(TypedDict):
    type: Literal["multicheckbox"]
    choices: list[str]


class ImageCheckboxConstraintDict(TypedDict):
    type: Literal["imagecheckbox"]
    choices: list[str]


ConstraintType = Union[
    NumberConstraintDict,
    SelectConstraintDict,
    CheckboxConstraintDict,
    MultiCheckboxConstraintDict,
    ImageCheckboxConstraintDict,
]


def create_number_constraint(
    minimum: int = 1, maximum: int = 999, step: float = 1.0
) -> NumberConstraintDict:
    return NumberConstraintDict(
        type="number",
        minimum=minimum,
        maximum=maximum,
        step=step,
    )


def create_select_constraint(choices: list[str]) -> SelectConstraintDict:
    return SelectConstraintDict(type="select", choices=choices)


def create_checkbox_constraint() -> CheckboxConstraintDict:
    return CheckboxConstraintDict(type="checkbox")


def create_multicheckbox_constraint(choices: list[str]) -> MultiCheckboxConstraintDict:
    return MultiCheckboxConstraintDict(type="multicheckbox", choices=choices)


def create_image_checkbox_constraint(choices: list[str]) -> ImageCheckboxConstraintDict:
    return ImageCheckboxConstraintDict(type="imagecheckbox", choices=choices)
