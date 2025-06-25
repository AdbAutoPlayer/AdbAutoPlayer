"""AFK Stages Mixin."""

import logging
from time import sleep

from adb_auto_player.decorators import register_command, register_custom_routine_choice
from adb_auto_player.exceptions import (
    AutoPlayerError,
    AutoPlayerWarningError,
)
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.image_manipulation import CropRegions
from adb_auto_player.util import SummaryGenerator

from ..base import AFKJourneyBase
from ..battle_state import Mode
from ..gui_category import AFKJCategory


class AFKStagesMixin(AFKJourneyBase):
    """AFK Stages Mixin."""

    @register_command(
        name="AFKStages",
        gui=GUIMetadata(
            label="AFK Stages",
            category=AFKJCategory.GAME_MODES,
        ),
        kwargs={"season": False},
    )
    @register_command(
        name="SeasonTalentStages",
        gui=GUIMetadata(
            label="Season Talent Stages",
            category=AFKJCategory.GAME_MODES,
        ),
        kwargs={"season": True},
    )
    @register_custom_routine_choice(
        label="AFK Stages",
        kwargs={"season": False},
    )
    @register_custom_routine_choice(
        label="Season Talent Stages",
        kwargs={"season": True},
    )
    def push_afk_stages(self, season: bool) -> None:
        """Entry for pushing AFK Stages.

        Args:
            season: Push Season Stage if True otherwise push regular AFK Stages
        """
        self.start_up()
        self.battle_state.mode = Mode.AFK_STAGES
        self.battle_state.is_season_talent_stages = season
        try:
            self._start_afk_stage()
        except AutoPlayerWarningError as e:
            logging.warning(f"{e}")
            return
        except AutoPlayerError as e:
            logging.error(f"{e}")
            return
        return

    def _start_afk_stage(self) -> None:
        """Start push."""
        stages_pushed: int = 0
        logging.info(f"Pushing: {self.battle_state.section_header}")
        self.navigate_to_afk_stages_screen()
        self.check_stages_are_available()
        self._select_afk_stage()
        while self._handle_battle_screen(
            self.get_config().afk_stages.use_suggested_formations,
            self.get_config().afk_stages.skip_manual_formations,
        ):
            stages_pushed += 1
            logging.info(f"{self.battle_state.section_header} pushed: {stages_pushed}")
            if self.battle_state.section_header:
                SummaryGenerator.increment(self.battle_state.section_header, "Pushed")

    def _select_afk_stage(self) -> None:
        """Selects an AFK stage template."""
        if self.battle_state.is_season_talent_stages:
            logging.debug("Clicking Talent Trials button")
            self.tap(Point(x=300, y=1610), scale=True)
        else:
            logging.debug("Clicking Battle button")
            self.tap(Point(x=800, y=1610), scale=True)
        sleep(2)
        if confirm := self.game_find_template_match(
            template="navigation/confirm.png",
            crop_regions=CropRegions(left=0.5, top=0.5),
        ):
            self.tap(confirm)

    def check_stages_are_available(self) -> None:
        if (
            not self.battle_state.is_season_talent_stages
            and self.game_find_template_match(
                "afk_stages/talent_trials_large.png",
                crop_regions=CropRegions(left=0.2, right=0.2, top=0.5),
            )
        ):
            raise AutoPlayerWarningError(
                "AFK Stages not available are they already cleared? Exiting..."
            )
