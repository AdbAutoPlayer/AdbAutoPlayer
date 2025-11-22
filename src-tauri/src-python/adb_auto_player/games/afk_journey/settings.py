"""AFK Journey Settings Module."""

from enum import StrEnum
from typing import Annotated

from adb_auto_player.models.pydantic import TaskListSettings, TomlSettings
from pydantic import BaseModel, Field

from .heroes import HeroesEnum

# Type constraints
PositiveInt = Annotated[int, Field(ge=1, le=999)]
FormationsInt = Annotated[int, Field(ge=1, le=10)]


# Enums
class TowerEnum(StrEnum):
    """All faction towers."""

    Lightbearer = "Lightbearer"
    Wilder = "Wilder"
    Graveborn = "Graveborn"
    Mauler = "Mauler"


# Models
class GeneralSettings(BaseModel):
    """General Settings model."""

    assist_limit: PositiveInt = Field(
        default=20, alias="Assist Limit", title="Assist Limit"
    )
    excluded_heroes: list[HeroesEnum] = Field(
        default_factory=list,
        title="Exclude Heroes",
        alias="Exclude Heroes",
        json_schema_extra={
            "formType": "AlnumGroupedCheckboxArray",
        },
    )


class CommonBattleModeSettings(BaseModel):
    """Common Settings shared across battle modes."""

    attempts: PositiveInt = Field(default=5, alias="Attempts", title="Attempts")
    formations: FormationsInt = Field(
        default=10, alias="Formations", title="Formations"
    )
    use_suggested_formations: bool = Field(
        default=True,
        alias="Suggested Formations",
        title="Suggested Formations",
    )
    use_current_formation_before_suggested_formation: bool = Field(
        default=True,
        alias="Start with current Formation",
        title="Start with current Formation",
    )
    spend_gold: bool = Field(default=False, alias="Spend Gold", title="Spend Gold")


class BattleAllowsManualSettings(CommonBattleModeSettings):
    """Battle modes that allow manual battles."""

    skip_manual_formations: bool = Field(
        default=False,
        alias="Skip Manual Formations",
        title="Skip Manual Formations",
    )
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
        title="Towers",
        json_schema_extra={
            "formType": "ImageCheckboxArray",
            "assetPath": "AFKJourney/Towers",
        },
    )


class ArcaneLabyrinthSettings(BaseModel):
    """Arcane Labyrinth Settings model."""

    difficulty: int = Field(
        ge=1, le=15, default=13, alias="Difficulty", title="Difficulty"
    )
    key_quota: int = Field(
        ge=1, le=9999, default=2700, alias="Key Quota", title="Key Quota"
    )


class DreamRealmSettings(BaseModel):
    """Dream Realm Settings model."""

    spend_gold: bool = Field(default=False, alias="Spend Gold", title="Spend Gold")


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
        default=50,
        alias="Titan Reaver Proxy Battle Limit",
        title="Titan Reaver Proxy Battle Limit",
    )


class Settings(TomlSettings):
    """Settings model."""

    general: GeneralSettings = Field(
        default_factory=GeneralSettings, alias="General", title="General"
    )
    dailies: DailiesSettings = Field(
        default_factory=DailiesSettings, alias="Dailies", title="Dailies"
    )
    afk_stages: AFKStagesSettings = Field(
        default_factory=AFKStagesSettings, alias="AFK Stages", title="AFK Stages"
    )
    duras_trials: DurasTrialsSettings = Field(
        default_factory=DurasTrialsSettings,
        alias="Dura's Trials",
        title="Dura's Trials",
    )
    legend_trials: LegendTrialsSettings = Field(
        default_factory=LegendTrialsSettings,
        alias="Legend Trial",
        title="Legend Trial",
    )
    arcane_labyrinth: ArcaneLabyrinthSettings = Field(
        default_factory=ArcaneLabyrinthSettings,
        alias="Arcane Labyrinth",
        title="Arcane Labyrinth",
    )
    dream_realm: DreamRealmSettings = Field(
        default_factory=DreamRealmSettings,
        alias="Dream Realm",
        title="Dream Realm",
    )
    claim_afk_rewards: ClaimAFKRewardsSettings = Field(
        default_factory=ClaimAFKRewardsSettings,
        alias="Claim AFK Rewards",
        title="Claim AFK Rewards",
    )
    titan_reaver_proxy_battles: TitanReaverProxyBattlesSettings = Field(
        default_factory=TitanReaverProxyBattlesSettings,
        alias="Titan Reaver Proxy Battles",
        title="Titan Reaver Proxy Battles",
    )
    custom_routine_one: TaskListSettings = Field(
        default_factory=TaskListSettings,
        alias="Custom Routine 1",
        title="Custom Routine 1",
    )
    custom_routine_two: TaskListSettings = Field(
        default_factory=TaskListSettings,
        alias="Custom Routine 2",
        title="Custom Routine 2",
    )
    custom_routine_three: TaskListSettings = Field(
        default_factory=TaskListSettings,
        alias="Custom Routine 3",
        title="Custom Routine 3",
    )
