from pydantic import BaseModel, Field
import tomllib
from pathlib import Path


class GeneralConfig(BaseModel):
    excluded_heroes: list[str] = Field(default_factory=[])  # type: ignore
    assist_limit: int = 20


class AFKStagesConfig(BaseModel):
    attempts: int = 5
    formations: int = 7
    use_suggested_formations: bool = True
    push_both_modes: bool = True
    spend_gold: bool = False


class DurasTrialsConfig(BaseModel):
    attempts: int = 5
    formations: int = 7
    use_suggested_formations: bool = True
    spend_gold: bool = False


class LegendTrialsConfig(BaseModel):
    attempts: int = 5
    formations: int = 7
    use_suggested_formations: bool = True
    spend_gold: bool = False


class Config(BaseModel):
    general: GeneralConfig
    afk_stages: AFKStagesConfig
    duras_trials: DurasTrialsConfig
    legend_trials: LegendTrialsConfig

    @classmethod
    def from_toml(cls, file_path: Path):
        with open(file_path, "rb") as f:
            toml_data = tomllib.load(f)

        return cls(**toml_data)
