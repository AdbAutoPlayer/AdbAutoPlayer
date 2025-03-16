"""Infinity Nikki Config Module."""

from typing import Annotated

from adb_auto_player import ConfigBase
from pydantic import BaseModel, Field

# Type constraints
PositiveInt = Annotated[int, Field(ge=1, le=999)]


# Models
class SheepMinigameConfig(BaseModel):
    """Sheep Minigame config model."""

    # perfect clear gives 1350 bling => bling cap is 160k => 160000 / 1350 =~ 119
    runs: PositiveInt = Field(default=119, alias="Runs")


class Config(ConfigBase):
    """Infinity Nikki config model."""

    sheep_minigame_config: SheepMinigameConfig = Field(alias="Sheep Minigame")
