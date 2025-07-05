from dataclasses import dataclass
from enum import StrEnum


class Mode(StrEnum):
    DURAS_TRIALS = "Dura's Trials"
    DURAS_NIGHTMARE_TRIALS = "Dura's Nightmare Trials"
    AFK_STAGES = "AFK Stages"
    SEASON_TALENT_STAGES = "Season Talent Stages"
    LEGEND_TRIALS = "Season Legend Trial"

    def is_duras(self) -> bool:
        return self in {Mode.DURAS_TRIALS, Mode.DURAS_NIGHTMARE_TRIALS}

    def is_afk_stages(self) -> bool:
        return self in {Mode.AFK_STAGES, Mode.SEASON_TALENT_STAGES}


@dataclass
class BattleState:
    mode: Mode | None = None
    max_attempts_reached: bool = False
    formation_num: int = 0
    faction: str | None = None

    @property
    def section_header(self) -> str | None:
        if not self.mode:
            return None
        if self.mode == Mode.LEGEND_TRIALS:
            if not self.faction:
                return "Legend Trial"
            return f"Legend Trial - {self.faction} Tower"
        return self.mode.value

    @property
    def faction_lower(self) -> str | None:
        if self.faction:
            return self.faction.lower()
        return None
