"""Avatar Realms Collide Config Module."""

from enum import StrEnum, auto

from adb_auto_player import ConfigBase
from pydantic import BaseModel, Field


class ResourceEnum(StrEnum):
    """Resources."""

    @staticmethod
    def _generate_next_value_(name, start, count, last_values):
        return name

    Food = auto()
    Wood = auto()
    Stone = auto()
    Gold = auto()


DEFAULT_RESOURCES = list(ResourceEnum.__members__.values())


class PercentOffEnum(StrEnum):
    """Percentage off."""

    percent_off_70 = "-70%"
    percent_off_80 = "-80%"


DEFAULT_PERCENTAGES_OFF = list(PercentOffEnum.__members__.values())


class AutoPlayConfig(BaseModel):
    """AutoPlay config model."""

    building_slot_1: bool = Field(default=True, alias="Build Slot 1")
    building_slot_2: bool = Field(default=True, alias="Build Slot 2")
    purchase_seal_of_solidarity: bool = Field(
        default=False,
        alias="Purchase Seal of Solidarity",
    )

    research: bool = Field(default=True, alias="Research")
    military_first: bool = Field(default=True, alias="Research Military First")

    recruit_troops: bool = Field(default=True, alias="Recruit Troops")
    upgrade_troops: bool = Field(default=True, alias="Upgrade Troops")

    alliance_research: bool = Field(default=True, alias="Alliance Research")
    alliance_gifts: bool = Field(default=True, alias="Alliance Gifts")

    collect_campaign_chest: bool = Field(default=True, alias="Collect Campaign Chest")
    collect_free_scrolls: bool = Field(default=True, alias="Collect Free Scrolls")

    expedition: bool = Field(default=True, alias="Expedition")
    skip_hold_position_check: bool = Field(
        default=False, alias="Skip Hold Position Check"
    )

    gather_resources: list[ResourceEnum] = Field(
        default_factory=lambda: DEFAULT_RESOURCES,
        alias="Gather Resources",
        json_schema_extra={
            "constraint_type": "multicheckbox",
            "default_value": DEFAULT_RESOURCES,
        },
    )


class TradingPostConfig(BaseModel):
    """TradingPost config model."""

    row_1_resources: bool = Field(default=True, alias="Row 1: Resources")
    row_2_speedups: bool = Field(default=True, alias="Row 2: Speedups")
    row_3_hero_upgrade_items: bool = Field(
        default=False,
        alias="Row 3: Hero Upgrade Items",
    )
    row_4_boosts_and_teleports: bool = Field(
        default=False,
        alias="Row 4: Boosts & Teleports",
    )
    gem_legendary_spirit_badge: list[PercentOffEnum] = Field(
        default_factory=lambda: DEFAULT_PERCENTAGES_OFF,
        alias="Gem: Legendary Spirit Badge",
        json_schema_extra={
            "constraint_type": "multicheckbox",
            "default_value": DEFAULT_PERCENTAGES_OFF,
        },
    )


class Config(ConfigBase):
    """Avatar Realms Collide config model."""

    auto_play: AutoPlayConfig = Field(alias="Auto Play")
    trading_post: TradingPostConfig = Field(alias="Trading Post")
