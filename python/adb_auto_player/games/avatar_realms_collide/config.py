"""Avatar Realms Collide Config Module."""

from enum import StrEnum, auto

from adb_auto_player import ConfigBase
from pydantic import BaseModel, Field


class ResourceEnum(StrEnum):
    """All faction towers."""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    Food = auto()
    Wood = auto()
    Stone = auto()
    Gold = auto()


class AutoPlayConfig(BaseModel):
    """AutoPlay config model."""

    research: bool = Field(default=True, alias="Research")
    build: bool = Field(default=True, alias="Build")
    recruit_troops: bool = Field(default=True, alias="Recruit Troops")
    alliance_research_and_gifts: bool = Field(
        default=True, alias="Alliance Research & Gifts"
    )
    collect_campaign_chest: bool = Field(default=True, alias="Collect Campaign Chest")
    gather_resources: list[ResourceEnum] = Field(
        default_factory=list,
        alias="Gather Resources",
    )


class Config(ConfigBase):
    """Avatar Realms Collide config model."""

    auto_play_config: AutoPlayConfig = Field(alias="Auto Play")
