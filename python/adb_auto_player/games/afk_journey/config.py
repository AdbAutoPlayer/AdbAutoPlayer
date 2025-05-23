"""AFK Journey Config Module."""

from enum import StrEnum, auto
from typing import Annotated

from adb_auto_player import ConfigBase
from pydantic import BaseModel, Field

# Type constraints
PositiveInt = Annotated[int, Field(ge=1, le=999)]
FormationsInt = Annotated[int, Field(ge=1, le=7)]


# Enums
class HeroesEnum(StrEnum):
    """All heroes."""

    def _generate_next_value_(name, start, count, last_values):  # noqa: N805
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
    """All faction towers."""

    def _generate_next_value_(name, start, count, last_values):  # noqa: N805
        return name

    Lightbearer = auto()
    Wilder = auto()
    Graveborn = auto()
    Mauler = auto()


# Models
class GeneralConfig(BaseModel):
    """General config model."""

    excluded_heroes: list[HeroesEnum] = Field(
        default_factory=list,
        alias="Exclude Heroes",
        json_schema_extra={
            "constraint_type": "multicheckbox",
            "group_alphabetically": True,
        },
    )
    assist_limit: PositiveInt = Field(default=20, alias="Assist Limit")


class AFKStagesConfig(BaseModel):
    """AFK Stages config model."""

    attempts: PositiveInt = Field(default=5, alias="Attempts")
    formations: FormationsInt = Field(default=7, alias="Formations")
    use_suggested_formations: bool = Field(default=True, alias="Suggested Formations")
    push_both_modes: bool = Field(default=True, alias="Both Modes")
    spend_gold: bool = Field(default=False, alias="Spend Gold")
    repeat: bool = Field(default=True, alias="Repeat")
    skip_manual_formations: bool = Field(default=False, alias="Skip Manual Formations")


class DurasTrialsConfig(BaseModel):
    """Dura's Trials config model."""

    attempts: PositiveInt = Field(default=2, alias="Attempts")
    formations: FormationsInt = Field(default=7, alias="Formations")
    use_suggested_formations: bool = Field(default=True, alias="Suggested Formations")
    spend_gold: bool = Field(default=False, alias="Spend Gold")


DEFAULT_TOWERS = list(TowerEnum.__members__.values())


class LegendTrialsConfig(BaseModel):
    """Legend Trials config model."""

    attempts: PositiveInt = Field(default=5, alias="Attempts")
    formations: FormationsInt = Field(default=7, alias="Formations")
    use_suggested_formations: bool = Field(default=True, alias="Suggested Formations")
    spend_gold: bool = Field(default=False, alias="Spend Gold")
    towers: list[TowerEnum] = Field(
        default_factory=lambda: DEFAULT_TOWERS,
        alias="Towers",
        json_schema_extra={
            "constraint_type": "imagecheckbox",
            "default_value": DEFAULT_TOWERS,
            "image_dir_path": "afk_journey",
        },
    )


class ArcaneLabyrinthConfig(BaseModel):
    """Arcane Labyrinth config model."""

    difficulty: int = Field(ge=1, le=15, default=13, alias="Difficulty")
    key_quota: int = Field(ge=1, le=9999, default=2700, alias="Key Quota")


class DreamRealmConfig(BaseModel):
    """Dream Realm config model."""

    spend_gold: bool = Field(default=False, alias="Spend Gold")


class DailiesConfig(BaseModel):
    """Dailies config model."""

    buy_discount_affinity: bool = Field(default=True, alias="Buy Discount Affinity")
    buy_all_affinity: bool = Field(default=False, alias="Buy All Affinity")
    single_pull: bool = Field(default=False, alias="Single Pull")
    arena_battle: bool = Field(default=False, alias="Arena Battle")


class MyCustomRoutineConfig(BaseModel):
    """My Custom Routine config model."""

    skip_daily_tasks_today: bool = Field(default=False, alias="Skip Daily Tasks Today")
    daily_tasks: list = Field(
        default_factory=list,
        alias="Daily Tasks",
        json_schema_extra={
            "constraint_type": "MyCustomRoutine",
            "default_value": [],
        },
    )
    repeating_tasks: list = Field(
        default_factory=list,
        alias="Repeating Tasks",
        json_schema_extra={
            "constraint_type": "MyCustomRoutine",
            "default_value": [],
        },
    )


class Config(ConfigBase):
    """Config model."""

    general: GeneralConfig = Field(alias="General")
    dailies: DailiesConfig = Field(alias="Dailies")
    afk_stages: AFKStagesConfig = Field(alias="AFK Stages")
    duras_trials: DurasTrialsConfig = Field(alias="Dura's Trials")
    legend_trials: LegendTrialsConfig = Field(alias="Legend Trial")
    arcane_labyrinth: ArcaneLabyrinthConfig = Field(alias="Arcane Labyrinth")
    dream_realm: DreamRealmConfig = Field(alias="Dream Realm")
    my_custom_routine: MyCustomRoutineConfig = Field(alias="My Custom Routine")
