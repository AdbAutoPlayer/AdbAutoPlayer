"""Guild Member Scan — public entry point."""

import datetime
import logging
import shutil

from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import AutoPlayerWarningError
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.ocr import OCRBackend

from ._guild_scan_activeness import _GuildScanActivenessMixin


class GuildMemberScanMixin(_GuildScanActivenessMixin):
    """Guild Member Scan Mixin — thin orchestration layer."""

    @register_command(
        name="GuildManagerScan",
        gui=GUIMetadata(
            label="Guild Manager Scan",
            category=AFKJCategory.EVENTS_AND_OTHER,
            tooltip=(
                "Scan rankings from Dream Realm and Supreme Arena for guild management"
            ),
        ),
    )
    def run_guild_manager_scan(self) -> None:
        """Export rankings from Dream Realm to a CSV file."""
        api_url = self.settings.guild_manager_scan.guild_members_api_url
        prefix = "https://"
        suffix = ".supabase.co/rest/v1/guild_states"
        if not api_url or not (api_url.startswith(prefix) and suffix in api_url):
            raise AutoPlayerWarningError(
                "Dream Realm Rankings requires a valid Guild Members API URL "
                "pointing to a Supabase guild_states endpoint "
                "(https://<project>.supabase.co/rest/v1/guild_states) "
                "configured in settings."
            )

        self.start_up(device_streaming=False)
        self._ensure_optional_packages()
        ocr_backend, fallback = self._select_ocr_backend()
        self._ocr_debug: list[dict] | None = (
            [] if self.settings.guild_manager_scan.debug_ocr else None
        )
        self._screenshot_dir = None
        if self.settings.guild_manager_scan.debug_ocr:
            data_root = SettingsLoader.get_app_config_dir()
            self._screenshot_dir = data_root / "data" / "screenshots"
            if self._screenshot_dir.exists():
                shutil.rmtree(self._screenshot_dir)
            self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        guild_members = self._fetch_guild_members()
        self._guild_members = guild_members

        rankings = self._run_dream_realm_scan(ocr_backend, fallback, guild_members)
        self._save_rankings_to_json(rankings)
        self._save_ocr_debug()

        self._run_optional_guild_scans(ocr_backend, fallback, guild_members)

        self.navigate_to_world()

    def _run_optional_guild_scans(
        self,
        ocr_backend: OCRBackend,
        fallback: OCRBackend | None,
        guild_members: list[str],
    ) -> None:
        """Run the Supreme Arena, Guild Activeness, and AFK Stages scans if enabled."""
        today = datetime.datetime.now().strftime("%A")
        ignore_days = self.settings.guild_manager_scan.ignore_day_restrictions

        if self.settings.guild_manager_scan.scan_supreme_arena:
            if ignore_days or today in ("Monday", "Tuesday"):
                logging.info(
                    "Supreme Arena scan enabled. Starting Supreme Arena scan..."
                )
                try:
                    self._scan_supreme_arena(ocr_backend, fallback, guild_members)
                except Exception as e:
                    logging.error(f"Error scanning Supreme Arena: {e}")
                self._save_ocr_debug()
            else:
                logging.info(
                    f"Supreme Arena scan skipped — today is {today} "
                    "(runs on Monday and Tuesday only)."
                )

        if self.settings.guild_manager_scan.scan_guild_activeness:
            if ignore_days or today == "Sunday":
                logging.info("Guild Activeness scan enabled. Starting scan...")
                try:
                    self._scan_guild_activeness(ocr_backend, guild_members)
                except Exception as e:
                    logging.error(f"Error scanning Guild Activeness: {e}")
                self._save_ocr_debug()
            else:
                logging.info(
                    f"Guild Activeness scan skipped — today is {today} "
                    "(runs on Sunday only)."
                )

        if self.settings.guild_manager_scan.scan_afk_stages_rankings:
            logging.info("AFK Stages Ranking scan enabled. Starting scan...")
            try:
                self._scan_afk_stages_rankings(ocr_backend, fallback, guild_members)
            except Exception as e:
                logging.error(f"Error scanning AFK Stages Rankings: {e}")
            self._save_ocr_debug()
