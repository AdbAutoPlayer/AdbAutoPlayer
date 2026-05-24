"""HeroScannerMixin — thin delegation layer for the HeroScanner service."""

from __future__ import annotations

from functools import cached_property

from adb_auto_player.decorators.register_command import register_command
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.games.afk_journey.services import HeroScanner
from adb_auto_player.models.decorators import GUIMetadata


class HeroScannerMixin:
    """Mixin that exposes hero-scanning commands by delegating to HeroScanner.

    All scanning logic lives in
    :class:`adb_auto_player.games.afk_journey.services.HeroScanner`.
    This mixin only registers the GUI command and manages the service lifetime.

    Expects to be mixed into a class that provides Game and Navigation methods.
    """

    @cached_property
    def _hero_scanner(self) -> HeroScanner:
        """Lazily-initialised HeroScanner service."""
        return HeroScanner(self)  # ty: ignore[invalid-argument-type]

    @register_command(
        name="HeroScanner",
        gui=GUIMetadata(
            label="AFKJ Tracker Scan",
            category=AFKJCategory.EVENTS_AND_OTHER,
            tooltip="Scan your hero roster for the AFKJ Tracker website",
        ),
    )
    def scan_roster(self, total_heroes: int | None = None) -> None:
        """Scan the entire hero roster and write results to the backup tracker.

        Args:
            total_heroes: Optional scan limit. If None, inferred from settings.
        """
        self._hero_scanner.scan_roster(total_heroes)
