from typing import Annotated

from pydantic import BaseModel, Field
import tomllib
from pathlib import Path

from adb_auto_player.ipc import constraint

# Type constraints
PositiveInt = Annotated[int, Field(ge=1, le=999)]


# Models
class SheepMinigameConfig(BaseModel):
    runs: PositiveInt = Field(default=119, alias="Runs")


class Config(BaseModel):
    sheep_minigame_config: SheepMinigameConfig = Field(alias="Sheep Minigame")

    @classmethod
    def from_toml(cls, file_path: Path):
        with open(file_path, "rb") as f:
            toml_data = tomllib.load(f)

        return cls(**toml_data)

    @staticmethod
    def get_constraints() -> dict[str, dict[str, constraint.ConstraintType]]:
        return {
            "Sheep Minigame": {
                "Runs": constraint.create_number_constraint(),
            },
        }
