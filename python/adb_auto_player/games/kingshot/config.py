"""KingShot Collide Config Module."""

from enum import StrEnum, auto

from adb_auto_player import ConfigBase
from pydantic import BaseModel, Field


class ResourceEnum(StrEnum):
    """Resources."""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    Bread = auto()
    Wood = auto()
    Stone = auto()
    Iron = auto()


DEFAULT_RESOURCES = list(ResourceEnum.__members__.values())


class AutoPlayConfig(BaseModel):
    """AutoPlay config model."""

    gather_resources: list[ResourceEnum] = Field(
        default_factory=lambda: DEFAULT_RESOURCES,
        alias="Gather Resources",
        json_schema_extra={
            "constraint_type": "multicheckbox",
            "default_value": DEFAULT_RESOURCES,
        },
    )
    auto_join: bool = Field(
        default=False,
        alias="Rally Auto-Join",
    )


class Config(ConfigBase):
    """KingShot config model."""

    auto_play: AutoPlayConfig = Field(alias="Auto Play")
