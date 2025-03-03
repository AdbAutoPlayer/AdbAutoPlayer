from enum import StrEnum, auto
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
import tomllib
from pathlib import Path

from adb_auto_player.ipc import constraint

# Type constraints
PositiveInt = Annotated[int, Field(ge=1, le=999)]
FormationsInt = Annotated[int, Field(ge=1, le=7)]


# Enums
class HeroesEnum(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name.replace("_and_", " & ").replace("_", " ")

    Alsa = auto()
    Antandra = auto()
    Arden = auto()
    Atalanta = auto()
    Berial = auto()
    Bonnie = auto()
    Brutus = auto()
    Bryon = auto()
    Callan = auto()
    Carolina = auto()
    Cassadee = auto()
    Cecia = auto()
    Cryonaia = auto()
    Cyran = auto()
    Damian = auto()
    Dionel = auto()
    Dunlingr = auto()
    Eironn = auto()
    Elijah_and_Lailah = auto()
    Fae = auto()
    Faramor = auto()
    Florabelle = auto()
    Gerda = auto()
    Granny_Dahnie = auto()
    Harak = auto()
    Hewynn = auto()
    Hodgkin = auto()
    Hugin = auto()
    Igor = auto()
    Kafra = auto()
    Koko = auto()
    Korin = auto()
    Kruger = auto()
    Lenya = auto()
    LilyMay = auto()
    Lorsan = auto()
    Lucca = auto()
    Lucius = auto()
    Ludovic = auto()
    Lumont = auto()
    Lyca = auto()
    Marilee = auto()
    Mikola = auto()
    Mirael = auto()
    Nara = auto()
    Niru = auto()
    Odie = auto()
    Phraesto = auto()
    Reinier = auto()
    Rhys = auto()
    Rowan = auto()
    Salazer = auto()
    Satrana = auto()
    Scarlita = auto()
    Seth = auto()
    Shakir = auto()
    Shemira = auto()
    Silvina = auto()
    Sinbad = auto()
    Smokey = auto()
    Sonja = auto()
    Soren = auto()
    Talene = auto()
    Tasi = auto()
    Temesia = auto()
    Thoran = auto()
    Ulmus = auto()
    Vala = auto()
    Valen = auto()
    Valka = auto()
    Viperian = auto()
    Walker = auto()


class TowerEnum(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    Lightbearer = auto()
    Wilder = auto()
    Graveborn = auto()
    Mauler = auto()


# Models
class GeneralConfig(BaseModel):
    excluded_heroes: list[HeroesEnum] = Field(
        default_factory=list, alias="Exclude Heroes"
    )
    assist_limit: PositiveInt = Field(default=20, alias="Assist Limit")


class AFKStagesConfig(BaseModel):
    attempts: PositiveInt = Field(default=5, alias="Attempts")
    formations: FormationsInt = Field(default=7, alias="Formations")
    use_suggested_formations: bool = Field(default=True, alias="Suggested Formations")
    push_both_modes: bool = Field(default=True, alias="Both Modes")
    spend_gold: bool = Field(default=False, alias="Spend Gold")
    repeat: bool = Field(default=True, alias="Repeat")


class DurasTrialsConfig(BaseModel):
    attempts: PositiveInt = Field(default=2, alias="Attempts")
    formations: FormationsInt = Field(default=7, alias="Formations")
    use_suggested_formations: bool = Field(default=True, alias="Suggested Formations")
    spend_gold: bool = Field(default=False, alias="Spend Gold")


class LegendTrialsConfig(BaseModel):
    attempts: PositiveInt = Field(default=5, alias="Attempts")
    formations: FormationsInt = Field(default=7, alias="Formations")
    use_suggested_formations: bool = Field(default=True, alias="Suggested Formations")
    spend_gold: bool = Field(default=False, alias="Spend Gold")
    towers: list[TowerEnum] = Field(default_factory=list, alias="Towers")

    @field_validator("towers", mode="before")
    @classmethod
    def parse_towers(cls, v):
        if isinstance(v, list):
            return [TowerEnum(tower) for tower in v]
        return v


class ArcaneLabyrinthConfig(BaseModel):
    difficulty: int = Field(ge=1, le=15, default=13, alias="Difficulty")


class Config(BaseModel):
    general: GeneralConfig = Field(alias="General")
    afk_stages: AFKStagesConfig = Field(alias="AFK Stages")
    duras_trials: DurasTrialsConfig = Field(alias="Dura's Trials")
    legend_trials: LegendTrialsConfig = Field(alias="Legend Trial")
    arcane_labyrinth: ArcaneLabyrinthConfig = Field(alias="Arcane Labyrinth")

    @classmethod
    def from_toml(cls, file_path: Path):
        with open(file_path, "rb") as f:
            toml_data = tomllib.load(f)

        return cls(**toml_data)

    @staticmethod
    def get_constraints() -> dict[str, dict[str, constraint.ConstraintType]]:
        formations_constraint = constraint.create_number_constraint(maximum=7)

        return {
            "General": {
                "Exclude Heroes": constraint.create_multicheckbox_constraint(
                    [e.value for e in HeroesEnum]  # type: ignore
                ),
                "Assist Limit": constraint.create_number_constraint(),
            },
            "AFK Stages": {
                "Attempts": constraint.create_number_constraint(),
                "Formations": formations_constraint,
                "Suggested Formations": constraint.create_checkbox_constraint(),
                "Both Modes": constraint.create_checkbox_constraint(),
                "Spend Gold": constraint.create_checkbox_constraint(),
                "Repeat": constraint.create_checkbox_constraint(),
            },
            "Arcane Labyrinth": {
                "Difficulty": constraint.create_number_constraint(
                    minimum=1,
                    maximum=15,
                ),
            },
            "Dura's Trials": {
                "Attempts": constraint.create_number_constraint(),
                "Formations": formations_constraint,
                "Suggested Formations": constraint.create_checkbox_constraint(),
                "Spend Gold": constraint.create_checkbox_constraint(),
            },
            "Legend Trial": {
                "Attempts": constraint.create_number_constraint(),
                "Formations": formations_constraint,
                "Suggested Formations": constraint.create_checkbox_constraint(),
                "Spend Gold": constraint.create_checkbox_constraint(),
                "Towers": constraint.create_image_checkbox_constraint(
                    [e.value for e in TowerEnum]  # type: ignore
                ),
            },
        }
