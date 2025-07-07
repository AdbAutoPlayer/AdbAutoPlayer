"""AFK Journey Config Module."""

from enum import StrEnum, auto
from typing import Annotated

from adb_auto_player.models.pydantic import GameConfig, MyCustomRoutineConfig
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
    Athalia = auto()
    Baelran = auto()
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
    Daimon = auto()
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
    Indris = auto()
    Kafra = auto()
    Koko = auto()
    Korin = auto()
    Kruger = auto()
    Kulu = auto()
    Lenya = auto()
    Lily_May = auto()
    Lorsan = auto()
    Lucca = auto()
    Lucius = auto()
    Lucy = auto()
    Ludovic = auto()
    Lumont = auto()
    Lyca = auto()
    Marilee = auto()
    Mikola = auto()
    Mirael = auto()
    Nara = auto()
    Natsu = auto()
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
    Velara = auto()
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

    assist_limit: PositiveInt = Field(default=20, alias="Assist Limit")
    excluded_heroes: list[HeroesEnum] = Field(
        default_factory=list,
        alias="Exclude Heroes",
        json_schema_extra={
            "constraint_type": "multicheckbox",
            "group_alphabetically": True,
        },
    )


class CommonBattleModeConfig(BaseModel):
    """Common config shared across battle modes."""

    attempts: PositiveInt = Field(default=5, alias="Attempts")
    use_suggested_formations: bool = Field(default=True, alias="Suggested Formations")
    formations: FormationsInt = Field(default=7, alias="Formations")
    use_current_formation_before_suggested_formation: bool = Field(
        default=True,
        alias="Start with current Formation",
    )
    spend_gold: bool = Field(default=False, alias="Spend Gold")


class BattleAllowsManualConfig(CommonBattleModeConfig):
    """Battle modes that allow manual battles."""

    skip_manual_formations: bool = Field(default=False, alias="Skip Manual Formations")


class AFKStagesConfig(BattleAllowsManualConfig):
    """AFK Stages config model."""

    pass


class DurasTrialsConfig(CommonBattleModeConfig):
    """Dura's Trials config model."""

    pass


DEFAULT_TOWERS = list(TowerEnum.__members__.values())


class LegendTrialsConfig(BattleAllowsManualConfig):
    """Legend Trials config model."""

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
    buy_essences: bool = Field(default=False, alias="Buy Temporal Essences")
    essence_buy_count: int = Field(default=1, ge=1, le=4, alias="Essence Buy Count")


class ClaimAFKRewardsConfig(BaseModel):
    claim_stage_rewards: bool = Field(default=False, alias="Claim Stage Rewards")


class TitanReaverProxyBattlesConfig(BaseModel):
    proxy_battle_limit: PositiveInt = Field(
        default=50, alias="Titan Reaver Proxy Battle Limit"
    )


class Config(GameConfig):
    """Config model."""

    general: GeneralConfig = Field(alias="General")
    dailies: DailiesConfig = Field(alias="Dailies")
    afk_stages: AFKStagesConfig = Field(alias="AFK Stages")
    duras_trials: DurasTrialsConfig = Field(alias="Dura's Trials")
    legend_trials: LegendTrialsConfig = Field(alias="Legend Trial")
    arcane_labyrinth: ArcaneLabyrinthConfig = Field(alias="Arcane Labyrinth")
    dream_realm: DreamRealmConfig = Field(alias="Dream Realm")
    claim_afk_rewards: ClaimAFKRewardsConfig = Field(alias="Claim AFK Rewards")
    titan_reaver_proxy_battles: TitanReaverProxyBattlesConfig = Field(
        alias="Titan Reaver Proxy Battles"
    )
    custom_routine_one: MyCustomRoutineConfig = Field(alias="Custom Routine 1")
    custom_routine_two: MyCustomRoutineConfig = Field(alias="Custom Routine 2")
    custom_routine_three: MyCustomRoutineConfig = Field(alias="Custom Routine 3")
