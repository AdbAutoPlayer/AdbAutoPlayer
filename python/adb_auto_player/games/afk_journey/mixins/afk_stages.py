"""AFK Stages Mixin."""

import logging
from time import sleep

from adb_auto_player import (
    AutoPlayerError,
    AutoPlayerWarningError,
    Coordinates,
    CropRegions,
)
from adb_auto_player.decorators.register_command import GuiMetadata, register_command
from adb_auto_player.decorators.register_custom_routine_choice import (
    register_custom_routine_choice,
)
from adb_auto_player.games.afk_journey.base import (
    AFKJourneyBase,
)
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.util.summary_generator import SummaryGenerator


class AFKStagesMixin(AFKJourneyBase):
    """AFK Stages Mixin."""

    @register_command(
        name="AFKStages",
        gui=GuiMetadata(
            label="AFK Stages",
            category=AFKJCategory.GAME_MODES,
        ),
        kwargs={"season": False},
    )
    @register_command(
        name="SeasonTalentStages",
        gui=GuiMetadata(
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
        self.store[self.STORE_MODE] = self.MODE_AFK_STAGES

        self.store[self.STORE_SEASON] = season
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
        stages_name = self._get_current_afk_stages_name()

        logging.info(f"Pushing: {stages_name}")
        self.navigate_to_afk_stages_screen()
        self.check_stages_are_available()
        self._select_afk_stage()
        while self._handle_battle_screen(
            self.get_config().afk_stages.use_suggested_formations,
            self.get_config().afk_stages.skip_manual_formations,
        ):
            stages_pushed += 1
            logging.info(f"{stages_name}: {stages_pushed}")
            SummaryGenerator().add_count(f"{stages_name}")

    def _get_current_afk_stages_name(self) -> str:
        """Get stage name."""
        season = self.store.get(self.STORE_SEASON, False)
        if season:
            return "Season Talent Stages"
        return "AFK Stages"

    def _select_afk_stage(self) -> None:
        """Selects an AFK stage template."""
        if self.store.get(self.STORE_SEASON, False):
            logging.debug("Clicking Talent Trials button")
            self.tap(Coordinates(x=300, y=1610), scale=True)
        else:
            logging.debug("Clicking Battle button")
            self.tap(Coordinates(x=800, y=1610), scale=True)
        sleep(2)
        confirm = self.game_find_template_match(
            template="navigation/confirm.png", crop=CropRegions(left=0.5, top=0.5)
        )
        if confirm:
            self.tap(Coordinates(*confirm))

    def check_stages_are_available(self) -> None:
        if not self.store[self.STORE_SEASON] and self.game_find_template_match(
            "afk_stages/talent_trials_large.png",
            crop=CropRegions(left=0.2, right=0.2, top=0.5),
        ):
            raise AutoPlayerWarningError(
                "AFK Stages not available are they already cleared? Exiting..."
            )
