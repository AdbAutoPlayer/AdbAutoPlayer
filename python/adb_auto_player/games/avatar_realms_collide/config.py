"""Avatar Realms Collide Config Module."""

from adb_auto_player import ConfigBase
from pydantic import BaseModel, Field


class AutoPlayConfig(BaseModel):
    """AutoPlay config model."""

    research: bool = Field(default=True, alias="Research")
    build: bool = Field(default=True, alias="Build")
    recruit_troops: bool = Field(default=True, alias="Recruit Troops")
    alliance_research_and_gifts: bool = Field(
        default=True, alias="Alliance Research & Gifts"
    )
    collect_campaign_chest: bool = Field(default=True, alias="Collect Campaign Chest")
    gather_resources: bool = Field(default=True, alias="Gather Resources")


class Config(ConfigBase):
    """Avatar Realms Collide config model."""

    auto_play_config: AutoPlayConfig = Field(alias="Auto Play")
