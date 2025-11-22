"""Play Store Settings Module."""

from enum import StrEnum, auto
from typing import Annotated

from adb_auto_player.models.pydantic import TomlSettings
from pydantic import BaseModel, Field

# Type constraints
PositiveInt = Annotated[int, Field(ge=1, le=999)]


# Models
class SectionNumbersSettings(BaseModel):
    """For Testing GUI."""

    integer_number: PositiveInt = Field(default=119, title="Integer")
    float_number: float = Field(
        default=5.5,
        title="Float",
        ge=1,
        le=9,
        json_schema_extra={
            "step": 0.5,
        },
    )


class SectionTextSettings(BaseModel):
    """For Testing GUI."""

    regex_start_with_a: str = Field(
        default="a",
        title="Regex Start With a",
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
    """Section Select and Choice Settings model."""

    checkbox: bool = Field(default=True, title="Checkbox")
    multicheckbox_alpha: list[TestEnum] = Field(
        default_factory=list,
        title="MultiCheckbox alpha",
        json_schema_extra={
            "formType": "AlnumGroupedCheckboxArray",
        },
    )
    multicheckbox: list[TestEnum] = Field(
        default_factory=list,
        title="MultiCheckbox",
    )


class Settings(TomlSettings):
    """Play Store Settings model."""

    section_numbers: SectionNumbersSettings = Field(title="Numbers")
    section_text: SectionTextSettings = Field(title="Text")
    section_select: SectionSelectAndChoice = Field(title="Select and Choice")
