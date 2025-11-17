"""AFK Journey Settings Module."""

from enum import StrEnum, auto
from typing import Annotated

from adb_auto_player.models.pydantic import GameSettings, MyCustomRoutineSettings
from pydantic import BaseModel, Field

from .heroes import HeroesEnum

# Type constraints
PositiveInt = Annotated[int, Field(ge=1, le=999)]
FormationsInt = Annotated[int, Field(ge=1, le=10)]


# Enums
class TowerEnum(StrEnum):
    """All faction towers."""

    def _generate_next_value_(name, start, count, last_values):  # noqa: N805
        return name

    Lightbearer = auto()
    Wilder = auto()
    Graveborn = auto()
    Mauler = auto()


# Models
class GeneralSettings(BaseModel):
    """General Settings model."""

    assist_limit: PositiveInt = Field(default=20, alias="Assist Limit")
    excluded_heroes: list[HeroesEnum] = Field(
        default_factory=list,
        alias="Exclude Heroes",
        json_schema_extra={
            "constraint_type": "multicheckbox",
            "group_alphabetically": True,
        },
    )


class CommonBattleModeSettings(BaseModel):
    """Common Settings shared across battle modes."""

    attempts: PositiveInt = Field(default=5, alias="Attempts")
    formations: FormationsInt = Field(default=10, alias="Formations")
    use_suggested_formations: bool = Field(default=True, alias="Suggested Formations")
    use_current_formation_before_suggested_formation: bool = Field(
        default=True,
        alias="Start with current Formation",
    )
    spend_gold: bool = Field(default=False, alias="Spend Gold")


class BattleAllowsManualSettings(CommonBattleModeSettings):
    """Battle modes that allow manual battles."""

    skip_manual_formations: bool = Field(default=False, alias="Skip Manual Formations")
    run_manual_formations_last: bool = Field(
        default=True, alias="Run Manual Formations Last"
    )


class AFKStagesSettings(BattleAllowsManualSettings):
    """AFK Stages Settings model."""

    pass


class DurasTrialsSettings(BattleAllowsManualSettings):
    """Dura's Trials Settings model."""

    pass


DEFAULT_TOWERS = list(TowerEnum.__members__.values())


class LegendTrialsSettings(BattleAllowsManualSettings):
    """Legend Trials Settings model."""

    towers: list[TowerEnum] = Field(
        default_factory=lambda: DEFAULT_TOWERS,
        alias="Towers",
        json_schema_extra={
            "constraint_type": "imagecheckbox",
            "default_value": DEFAULT_TOWERS,
            "image_dir_path": "afk_journey",
        },
    )


class ArcaneLabyrinthSettings(BaseModel):
    """Arcane Labyrinth Settings model."""

    difficulty: int = Field(ge=1, le=15, default=13, alias="Difficulty")
    key_quota: int = Field(ge=1, le=9999, default=2700, alias="Key Quota")


class DreamRealmSettings(BaseModel):
    """Dream Realm Settings model."""

    spend_gold: bool = Field(default=False, alias="Spend Gold")


class DailiesSettings(BaseModel):
    """Dailies Settings model."""

    buy_discount_affinity: bool = Field(default=True, alias="Buy Discount Affinity")
    buy_all_affinity: bool = Field(default=False, alias="Buy All Affinity")
    single_pull: bool = Field(default=False, alias="Single Pull")
    arena_battle: bool = Field(default=False, alias="Arena Battle")
    buy_essences: bool = Field(default=False, alias="Buy Temporal Essences")
    essence_buy_count: int = Field(default=1, ge=1, le=4, alias="Essence Buy Count")


class ClaimAFKRewardsSettings(BaseModel):
    claim_stage_rewards: bool = Field(default=False, alias="Claim Stage Rewards")


class TitanReaverProxyBattlesSettings(BaseModel):
    proxy_battle_limit: PositiveInt = Field(
        default=50, alias="Titan Reaver Proxy Battle Limit"
    )


class Settings(GameSettings):
    """Settings model."""

    general: GeneralSettings = Field(alias="General")
    dailies: DailiesSettings = Field(alias="Dailies")
    afk_stages: AFKStagesSettings = Field(alias="AFK Stages")
    duras_trials: DurasTrialsSettings = Field(alias="Dura's Trials")
    legend_trials: LegendTrialsSettings = Field(alias="Legend Trial")
    arcane_labyrinth: ArcaneLabyrinthSettings = Field(alias="Arcane Labyrinth")
    dream_realm: DreamRealmSettings = Field(alias="Dream Realm")
    claim_afk_rewards: ClaimAFKRewardsSettings = Field(alias="Claim AFK Rewards")
    titan_reaver_proxy_battles: TitanReaverProxyBattlesSettings = Field(
        alias="Titan Reaver Proxy Battles"
    )
    custom_routine_one: MyCustomRoutineSettings = Field(alias="Custom Routine 1")
    custom_routine_two: MyCustomRoutineSettings = Field(alias="Custom Routine 2")
    custom_routine_three: MyCustomRoutineSettings = Field(alias="Custom Routine 3")
