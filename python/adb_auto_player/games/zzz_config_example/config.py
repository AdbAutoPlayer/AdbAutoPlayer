"""Play Store Config Module."""

from enum import StrEnum, auto
from typing import Annotated

from adb_auto_player.models.pydantic import GameConfig
from pydantic import BaseModel, Field

# Type constraints
PositiveInt = Annotated[int, Field(ge=1, le=999)]


# Models
class SectionNumbersConfig(BaseModel):
    """For Testing GUI."""

    integer_number: PositiveInt = Field(default=119, alias="Integer")
    float_number: float = Field(
        default=5.5,
        alias="Float",
        ge=1,
        le=9,
        json_schema_extra={
            "step": 0.5,
        },
    )


class SectionTextConfig(BaseModel):
    """For Testing GUI."""

    regex_start_with_a: str = Field(
        default="a",
        alias="Regex Start With a",
        json_schema_extra={
            "regex": "^a.*$",
            "title": "Text should start with lowercase a",
        },
    )


class TestEnum(StrEnum):
    """For Testing GUI."""

    A = auto()
    AB = auto()
    ABC = auto()
    B = auto()
    C = auto()
    X = auto()
    Y = auto()
    Z = auto()


class SectionSelectAndChoice(BaseModel):
    """Section Select and Choice config model."""

    checkbox: bool = Field(default=True, alias="Checkbox")
    multicheckbox_alpha: list[TestEnum] = Field(
        default_factory=list,
        alias="MultiCheckbox alpha",
        json_schema_extra={
            "constraint_type": "multicheckbox",
            "group_alphabetically": True,
        },
    )
    multicheckbox: list[TestEnum] = Field(
        default_factory=list,
        alias="MultiCheckbox",
        json_schema_extra={
            "constraint_type": "multicheckbox",
        },
    )


class Config(GameConfig):
    """Play Store config model."""

    section_numbers: SectionNumbersConfig = Field(alias="Numbers")
    section_text: SectionTextConfig = Field(alias="Text")
    section_select: SectionSelectAndChoice = Field(alias="Select and Choice")
