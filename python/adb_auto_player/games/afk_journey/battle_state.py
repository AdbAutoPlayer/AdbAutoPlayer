from dataclasses import dataclass
from enum import StrEnum


class Mode(StrEnum):
    DURAS_TRIALS = "Dura's Trials"
    AFK_STAGES = "AFK Stages"
    LEGEND_TRIALS = "Season Legend Trial"


@dataclass
class BattleState:
    is_season_talent_stages: bool = False
    mode: Mode | None = None
    max_attempts_reached: bool = False
    formation_num: int = 0

    @property
    def section_header(self) -> str | None:
        if not self.mode:
            return None
        if self.mode == Mode.AFK_STAGES and self.is_season_talent_stages:
            return "Season Talent Stages"
        return self.mode.value
