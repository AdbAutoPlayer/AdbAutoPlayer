"""Infinity Nikki Config Module."""

import tomllib
from pathlib import Path
from typing import Annotated

from adb_auto_player.ipc import constraint
from pydantic import BaseModel, Field

# Type constraints
PositiveInt = Annotated[int, Field(ge=1, le=999)]


# Models
class SheepMinigameConfig(BaseModel):
    """Sheep Minigame config model."""

    # perfect clear gives 1350 bling
    # bling cap is 160k
    # 160000 / 1350 =~ 119
    runs: PositiveInt = Field(default=119, alias="Runs")


class Config(BaseModel):
    """Infinity Nikki config model."""

    sheep_minigame_config: SheepMinigameConfig = Field(alias="Sheep Minigame")

    @classmethod
    def from_toml(cls, file_path: Path):
        """Create a Config instance from a TOML file."""
        with open(file_path, "rb") as f:
            toml_data = tomllib.load(f)

        return cls(**toml_data)

    @staticmethod
    def get_constraints() -> dict[str, dict[str, constraint.ConstraintType]]:
        """Get contraints from ADB Auto Player IPC."""
        return {
            "Sheep Minigame": {
                "Runs": constraint.create_number_constraint(),
            },
        }
