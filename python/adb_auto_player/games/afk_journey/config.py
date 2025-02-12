from enum import StrEnum, auto
from typing import Annotated

from pydantic import BaseModel, Field
import tomllib
from pathlib import Path

PositiveInt = Annotated[int, Field(ge=1, le=999)]
FormationsInt = Annotated[int, Field(ge=1, le=7)]


class HeroesEnum(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name

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
    ElijahAndLailah = "Elijah & Lailah"
    Fae = auto()
    Faramor = auto()
    Florabelle = auto()
    Gerda = auto()
    GrannyDahnie = "Granny Dahnie"
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


class GeneralConfig(BaseModel):
    excluded_heroes: list[HeroesEnum] = Field(default_factory=list)
    assist_limit: PositiveInt = 20


class AFKStagesConfig(BaseModel):
    attempts: PositiveInt = 5
    formations: FormationsInt = 7
    use_suggested_formations: bool = True
    push_both_modes: bool = True
    spend_gold: bool = False
    repeat: bool = True


class DurasTrialsConfig(BaseModel):
    attempts: PositiveInt = 2
    formations: FormationsInt = 7
    use_suggested_formations: bool = True
    spend_gold: bool = False


class TowerEnum(StrEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    Lightbearer = auto()
    Wilder = auto()
    Graveborn = auto()
    Mauler = auto()


class LegendTrialsConfig(BaseModel):
    attempts: PositiveInt = 5
    formations: FormationsInt = 7
    use_suggested_formations: bool = True
    spend_gold: bool = False
    towers: list[TowerEnum] = Field(default_factory=list)


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
