import datetime
import importlib.util
import json
import logging
import os
import re
import shutil
import site
import subprocess
import sys
import threading
import urllib.request
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

import cv2
from adb_auto_player.decorators import register_command
from adb_auto_player.exceptions import AutoPlayerWarningError, GameTimeoutError
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from adb_auto_player.models.ocr import OCRResult
from adb_auto_player.ocr import OCRBackend, RapidOCRBackend
from adb_auto_player.ocr.qwen2vl_backend import QwenVLOCRBackend

if TYPE_CHECKING:
    from typing import Any

    from adb_auto_player.games.afk_journey.settings import Settings
    from adb_auto_player.models.geometry import Point
    from adb_auto_player.ocr import OCRBackend

    class BaseClass:
        settings: Settings
        LANG_ERROR: str
        min_timeout: float
        fast_timeout: float
        device: Any
        template_timeout: float

        def start_up(self, device_streaming: bool = True) -> None: ...
        def navigate_to_world(self) -> None: ...
        def _enter_dr(self) -> None: ...
        def wait_for_template(self, *args, **kwargs) -> Any: ...
        def tap(self, *args, **kwargs) -> None: ...
        def swipe_left(self, *args, **kwargs) -> None: ...
        def game_find_template_match(self, *args, **kwargs) -> Any: ...
        def get_screenshot(self) -> Any: ...
        def swipe_up(self, *args, **kwargs) -> None: ...
        def sleep_action(self, *args, **kwargs) -> None: ...
        def _load_image(self, *args, **kwargs) -> Any: ...
        def press_back_button(self) -> None: ...
        def navigate_to_battle_modes_screen(self) -> None: ...
        def _find_in_battle_modes(self, *args, **kwargs) -> Any: ...
        def sleep_navigation(self) -> None: ...
else:
    BaseClass = object


class GuildMemberScanMixin(BaseClass):
    """Guild Member Scan Mixin."""

    # Screen region and tolerance constants
    _Y_MIN_DATE = 200
    _Y_MAX_DATE = 780
    _Y_DATE_ALIGNMENT_TOLERANCE = 30
    _X_MIN_DATE_TAB = 200
    _X_MAX_DATE_TAB = 1000
    _X_RANK_BOUNDARY = 200
    _X_SCORE_BOUNDARY = 700
    _X_SIDEBAR_BOUNDARY = 800
    _Y_MIN_FILTER = 400
    _Y_MAX_FILTER = 900
    _Y_MIN_RANKINGS = 780
    _Y_MAX_RANKINGS = 1800
    _Y_TAB_MIN = 1800
    _Y_GUILD_OFFSET = 45
    _Y_GUILD_OFFSET_PARTIAL = 25
    _Y_ROW_ALIGNMENT_TOLERANCE = 80
    _MIN_ROW_BLOCKS = 2
    _MAX_RANK_NUMBER = 500
    _MAX_DATE_LEN = 8
    _EXPECTED_DATE_PARTS = 2
    _MAX_ASCII_VAL = 127
    _MAX_NEW_NAMES_NO_CHANGE = 6
    _MIN_NAME_LENGTH = 2
    _MAX_SCROLLS = 25
    _MAX_SCROLLS_ACTIVENESS = 35
    _FUZZY_DEDUP_THRESHOLD = 0.75
    _MIN_NAME_ALNUM_RATIO = 0.5
    _MIN_UNRANKED_OBSERVATIONS = 2

    # Guild activeness scan constants
    # Bottom nav bar Y-coordinate for the guild-tab OCR search range
    _Y_GUILD_NAV_MIN = 1840
    _Y_GUILD_NAV_MAX = 1920
    # Swipe to reveal the hidden menu buttons (Members, etc.)
    # Drag from upper-right toward lower-left within the guild 3-D view
    _GUILD_SWIPE_SX = 700
    _GUILD_SWIPE_SY = 600
    _GUILD_SWIPE_EX = 300
    _GUILD_SWIPE_EY = 1200
    # After tapping Members: member rows appear in this Y range
    _Y_ACTIVENESS_MIN = 320
    _Y_ACTIVENESS_MAX = 1800
    # Activeness column: the numeric value sits on the right side of each card
    _X_ACTIVENESS_MIN = 500
    # Row Y-grouping tolerance for activeness list (pixels)
    _Y_ACTIVENESS_ROW_TOLERANCE = 60
    # Max search radius (in Y pixels) when pairing an activeness block to a name
    _Y_ACTIVENESS_PAIR_RADIUS = 120
    # Minimum activeness value to treat a numeric block as a real activeness score
    _MIN_ACTIVENESS_VALUE = 10
    # Max activeness value (sanity cap)
    _MAX_ACTIVENESS_VALUE = 9999
    # Minimum number of consecutive scrolls with no new members before stopping
    _MAX_NO_NEW_ACTIVENESS = 5
    # Max retry swipes when looking for the Members button
    _GUILD_NAV_SWIPE_MAX_ATTEMPTS = 2
    # Fuzzy-match threshold for single-name correction in activeness scan
    _GUILD_NAME_CORRECTION_THRESHOLD = 0.65
    # Guild Chest contribution ranking scan constants
    # Skip the static header panel (guild overview) at the top of the screen;
    # the ranking list entries start at y≈850.
    _Y_CHEST_CONTRIB_MIN = 850
    _Y_CHEST_CONTRIB_MAX = 1800
    # Names are on the left, chest values are on the right
    _X_CHEST_NAME_MAX = 480
    # Max Y distance to pair a chest value with a name
    _Y_CHEST_PAIR_RADIUS = 150
    # Max chest contribution value (sanity cap). Keeps OCR misreads like
    # "461" (chest icon read as "4" + real value "61") from being accepted.
    _MAX_CHEST_VALUE = 200
    _MAX_SCROLLS_CHEST = 44
    _MAX_NO_NEW_CHEST = 5
    _MAX_CHEST_NAV_RETRIES = 3
    # Rank numbers 1-N on the far left of the contribution ranking list
    _MAX_CHEST_RANK_NUMBER = 200
    # Rank badge circles sit at x≈105; member names start at x≈330+.
    # Use this threshold to distinguish rank number "67" from a member named "67".
    _X_CHEST_RANK_BADGE_MAX = 200
    # OCR often reads the chest icon as a prefix char (e.g. '￥8', '个8').
    # This regex matches an optional 1-3 non-digit prefix followed by digits.
    _RE_CHEST_VALUE = re.compile(r"^\D{0,3}(\d+)$")
    # Minimum similarity threshold between Florence-2 and RapidOCR names

    def __init__(self) -> None:
        """Initialize GuildMemberScanMixin."""
        super().__init__()

    def _select_ocr_backend(self) -> tuple[OCRBackend, OCRBackend | None]:
        """Choose the active OCR backend based on GPU availability and settings.

        Returns (primary, fallback).
        - If Qwen2-VL is enabled and GPU VRAM >= 6 GB: primary=QwenVLOCRBackend,
          fallback=RapidOCRBackend (PP-OCRv5, used when Qwen2-VL fails per frame).
        - Otherwise: primary=RapidOCRBackend (PP-OCRv5), fallback=None.
        """
        cfg = self.settings.guild_manager_scan

        rapid = RapidOCRBackend.pp_ocr_v5_rec()

        if cfg.use_qwen2vl and QwenVLOCRBackend.has_sufficient_vram():
            logging.info("GPU detected — using Qwen2-VL-2B as primary OCR.")
            return QwenVLOCRBackend(), rapid

        return rapid, None

    @staticmethod
    def _extras_dir() -> Path:
        """Return the directory used for runtime-installed optional packages."""
        return Path(sys.executable).parent.parent / "extras" / "guild_scan"

    @staticmethod
    def _activate_extras() -> None:
        """Add the extras directory to sys.path and persist it via a .pth file."""
        extras = GuildMemberScanMixin._extras_dir()
        if not extras.exists():
            return
        extras_str = str(extras)
        if extras_str not in sys.path:
            sys.path.append(extras_str)
        # Write a .pth file so future sessions pick up the directory automatically.
        try:
            for sp in site.getsitepackages():
                sp_path = Path(sp)
                if sp_path.exists():
                    (sp_path / "adb_guild_extras.pth").write_text(
                        extras_str + "\n", encoding="utf-8"
                    )
                    break
        except Exception as e:
            logging.warning(f"Could not write .pth persistence file: {e}")

    @staticmethod
    def _pip_install(
        packages: list[str],
        index_url: str | None = None,
        extra_index_url: str | None = None,
        reinstall: bool = False,
        no_deps: bool = False,
    ) -> bool:
        """Install packages into an isolated extras directory.

        Uses ``--target`` instead of the main venv so that already-loaded
        .dll/.pyd files (locked by Windows) are never touched. After a
        successful install the directory is added to ``sys.path`` for the
        current session and persisted via a .pth file for future sessions.
        """
        extras_dir = GuildMemberScanMixin._extras_dir()
        extras_dir.mkdir(parents=True, exist_ok=True)

        # Flags shared by both uv and pip
        index_flags: list[str] = []
        if index_url:
            index_flags += ["--index-url", index_url]
        elif extra_index_url:
            index_flags += [
                "--extra-index-url",
                extra_index_url,
                "--index-strategy",
                "unsafe-best-match",
            ]
        no_dep_flag = ["--no-deps"] if no_deps else []

        uv = shutil.which("uv")
        if uv:
            reinstall_flags = (
                [
                    f
                    for pkg in packages
                    for f in ("--reinstall-package", pkg.split(">=")[0].split("==")[0])
                ]
                if reinstall
                else []
            )
            cmd = [
                uv,
                "pip",
                "install",
                "--target",
                str(extras_dir),
                *reinstall_flags,
                *no_dep_flag,
                *index_flags,
                *packages,
            ]
        else:
            reinstall_flag = ["--force-reinstall"] if reinstall else []
            cmd = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--target",
                str(extras_dir),
                *reinstall_flag,
                *no_dep_flag,
                *index_flags,
                *packages,
            ]

        logging.info(f"Running: {' '.join(cmd)}")
        _ansi = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            # Heartbeat: log every 30 s so the user can see the app is not frozen.
            _stop = threading.Event()

            def _heartbeat() -> None:
                elapsed = 0
                while not _stop.wait(30):
                    elapsed += 30
                    logging.info(f"[install] still running… ({elapsed}s elapsed)")

            hb = threading.Thread(target=_heartbeat, daemon=True)
            hb.start()

            try:
                if process.stdout is not None:
                    for raw in process.stdout:
                        line = _ansi.sub("", raw).rstrip()
                        if line:
                            logging.info(f"[install] {line}")
            finally:
                _stop.set()

            process.wait()
            if process.returncode != 0:
                logging.error(f"Install failed (exit {process.returncode})")
                return False
            GuildMemberScanMixin._activate_extras()
            return True
        except Exception as e:
            logging.error(f"Install error: {e}")
            return False

    @staticmethod
    def _torch_metadata() -> tuple[bool, tuple[int, int]]:
        """Return (has_cuda, (major, minor)) from torch dist-info METADATA.

        Reads the text file only — no .pyd loading, so the file stays unlocked
        for reinstall. Returns (False, (0, 0)) if metadata is not found.
        """
        for dist_info in GuildMemberScanMixin._extras_dir().glob("torch-*.dist-info"):
            try:
                for line in (
                    (dist_info / "METADATA").read_text(errors="ignore").splitlines()
                ):
                    if line.startswith("Version:"):
                        raw = line.split(":", 1)[1].strip()
                        has_cuda = "+cu" in raw
                        base = raw.split("+")[0]
                        parts = base.split(".")
                        major = int(parts[0]) if len(parts) > 0 else 0
                        minor = int(parts[1]) if len(parts) > 1 else 0
                        return has_cuda, (major, minor)
            except Exception:
                pass
        return False, (0, 0)

    @staticmethod
    def _torch_has_cuda() -> bool:
        has_cuda, _ = GuildMemberScanMixin._torch_metadata()
        return has_cuda

    def _ensure_qwen2vl_packages(self, confirmed: bool) -> None:
        """Install or fix torch+Qwen2-VL deps, ensuring GPU (CUDA) support."""
        torch_present = importlib.util.find_spec("torch") is not None
        torchvision_present = importlib.util.find_spec("torchvision") is not None
        transformers_present = importlib.util.find_spec("transformers") is not None
        tiktoken_present = importlib.util.find_spec("tiktoken") is not None

        # Torch installed but CPU-only or too old (< 2.7 required by new transformers)
        has_cuda, torch_ver = self._torch_metadata()
        need_torch = (
            not torch_present
            or not torchvision_present
            or not has_cuda
            or torch_ver < (2, 7)
        )
        need_others = not transformers_present or not tiktoken_present

        if not need_torch and not need_others:
            return  # Everything already correct

        if not confirmed:
            logging.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logging.warning("  Qwen2-VL-2B: LARGE DOWNLOAD REQUIRED")
            logging.warning(
                "  Installing this backend requires approximately 5 GB of data"
            )
            logging.warning("  (PyTorch CUDA + model weights).")
            logging.warning(
                "  Make sure you have enough disk space and a stable connection."
            )
            logging.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            raise AutoPlayerWarningError(
                "Qwen2-VL-2B download not confirmed. "
                "Go to Settings → Guild Manager Scan and enable "
                "'Confirm Qwen2-VL Download (~2.2 GB)' to proceed."
            )

        logging.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logging.warning("  Qwen2-VL-2B: starting download (~2.2 GB).")
        logging.warning("  Please do not close the app...")
        logging.warning("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        # cu126 has torch 2.7+ wheels for Python 3.13 on Windows; cu124 tops at 2.6.
        cuda_index = "https://download.pytorch.org/whl/cu126"

        if need_torch:
            action = "Reinstalling" if torch_present else "Installing"
            logging.info(f"{action} PyTorch with CUDA 12.6 support...")
            if not self._pip_install(
                ["torch", "torchvision"],
                index_url=cuda_index,  # primary index → only CUDA wheels
                no_deps=True,  # deps (numpy etc.) already in extras_dir
                reinstall=torch_present,
            ):
                logging.warning(
                    "PyTorch (CUDA) installation failed — "
                    "Qwen2-VL will fall back to RapidOCR."
                )
                return

        if need_others:
            logging.info("Installing Qwen2-VL supporting packages...")
            if not self._pip_install(
                ["transformers>=4.45.0", "accelerate", "qwen-vl-utils", "tiktoken"]
            ):
                logging.warning(
                    "Qwen2-VL supporting packages failed — "
                    "falling back to RapidOCR for this run."
                )
                return

        logging.info(
            "Qwen2-VL-2B packages ready. "
            "The model weights (~2.2 GB) will be downloaded on first use."
        )

    def _ensure_optional_packages(self) -> None:
        """Auto-install optional OCR backends if the user has opted in."""
        self._activate_extras()
        scan_cfg = self.settings.guild_manager_scan

        if scan_cfg.use_qwen2vl:
            self._ensure_qwen2vl_packages(scan_cfg.confirm_qwen2vl_download)

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
        prefix = "https://clcozchimagtnzohuvsk.supabase.co/rest/v1/guild_states"
        if not api_url or not api_url.startswith(prefix):
            raise AutoPlayerWarningError(
                "Dream Realm Rankings requires a valid Guild Members API URL "
                f"starting with '{prefix}' configured in settings."
            )

        self.start_up(device_streaming=False)
        self._ensure_optional_packages()
        ocr_backend, fallback = self._select_ocr_backend()
        self._ocr_debug: list[dict] | None = (
            [] if self.settings.guild_manager_scan.debug_ocr else None
        )
        self._screenshot_dir: Path | None = None
        if self.settings.guild_manager_scan.debug_ocr:
            data_root = SettingsLoader.get_app_config_dir()
            self._screenshot_dir = data_root / "data" / "screenshots"
            if self._screenshot_dir.exists():
                shutil.rmtree(self._screenshot_dir)
            self._screenshot_dir.mkdir(parents=True, exist_ok=True)
        guild_members = self._fetch_guild_members()
        self._guild_members = guild_members

        # 1-5. Scan Dream Realm rankings
        rankings = self._run_dream_realm_scan(ocr_backend, fallback, guild_members)
        self._save_rankings_to_json(rankings)
        self._save_ocr_debug()

        today = datetime.datetime.now().strftime("%A")
        ignore_days = self.settings.guild_manager_scan.ignore_day_restrictions

        # 6. Optionally scan Supreme Arena rankings (Monday and Tuesday only)
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

        # 7. Optionally scan Guild member activeness (Sunday only).
        # RapidOCR handles bbox layout; Qwen supplements for multilingual names.
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

        # Clean up: go back to world
        self.navigate_to_world()

    def _run_dream_realm_scan(
        self,
        ocr_backend: OCRBackend,
        fallback: OCRBackend | None,
        guild_members: list[str],
    ) -> list[dict]:
        """Enter Dream Realm, select district rankings, scan configured dates."""
        # 1. Enter Dream Realm
        self._enter_dr()

        # 2. Select rankings button
        logging.info("Tapping Rankings button...")
        try:
            reward = self.wait_for_template(
                "dream_realm/dr_ranking.png",
                timeout_message="Could not find Rankings button.",
                timeout=self.min_timeout,
            )
            self.tap(reward)
            sleep(2)
        except GameTimeoutError as fail:
            logging.error(f"{fail} {self.LANG_ERROR}")
            raise

        # 3. Select District Rankings tab
        if not self._select_district_rankings(ocr_backend):
            raise AutoPlayerWarningError("Failed to select District Rankings tab.")

        # 4. Process dates until we have scanned the configured number of past dates
        processed_dates: set[str] = set()
        dates_to_scan = self.settings.guild_manager_scan.days_to_scan
        rankings: list[dict] = []

        today = datetime.datetime.now().strftime("%A")
        ignore_days = self.settings.guild_manager_scan.ignore_day_restrictions
        scan_today = self.settings.guild_manager_scan.scan_dr_today_on_sunday
        skip_today = not (scan_today and (today == "Sunday" or ignore_days))

        # We try for up to 5 iterations/scrolls to find and process the dates
        for _attempt in range(5):
            total_expected = dates_to_scan if skip_today else dates_to_scan + 1
            if len(processed_dates) >= total_expected:
                break

            date_tabs = self._find_date_tabs(ocr_backend)
            if not date_tabs:
                logging.warning("No date tabs visible in this view.")
                logging.info("Scrolling date bar left to reveal older dates...")
                self.swipe_left(y=758, sx=900, ex=200, duration=0.8)
                sleep(1.5)
                continue

            self._scan_visible_date_tabs(
                date_tabs,
                processed_dates,
                dates_to_scan,
                rankings,
                ocr_backend,
                fallback,
                guild_members,
                skip_today=skip_today,
            )

            # If we still need more dates, scroll the date bar to the left
            if len(processed_dates) < total_expected:
                logging.info("Scrolling date bar left to reveal older dates...")
                self.swipe_left(y=758, sx=900, ex=200, duration=0.8)
                sleep(1.5)

        return rankings

    def _scan_visible_date_tabs(
        self,
        date_tabs: list[OCRResult],
        processed_dates: set[str],
        dates_to_scan: int,
        rankings: list[dict],
        ocr_backend: OCRBackend,
        fallback: OCRBackend | None = None,
        guild_members: list[str] | None = None,
        skip_today: bool = True,
    ) -> None:
        """Scan visible date tabs, optionally ignoring the current day."""
        start_idx = 0
        if not processed_dates and skip_today:
            logging.info(
                f"Ignoring the first date tab (current day): {date_tabs[0].text}"
            )
            start_idx = 1
            processed_dates.add(date_tabs[0].text.strip())

        for tab in date_tabs[start_idx:]:
            date_name = tab.text.strip()
            if date_name not in processed_dates:
                logging.info(f"Processing date: {date_name}")

                # Tap the date tab
                self.tap(tab.box.center)
                sleep(2)

                # Set filter to Guild Members
                if not self._set_guild_members_filter(ocr_backend):
                    logging.warning(
                        "Could not set filter to Guild Members. "
                        "Rankings may contain all players."
                    )

                # Check for scroll-to-top button and click it if present
                scroll_top_btn = self.game_find_template_match(
                    "dream_realm/scroll_top.png",
                    threshold=ConfidenceValue("80%"),
                )
                if scroll_top_btn:
                    logging.info(
                        "Found scroll-to-top button, tapping to reset list to top."
                    )
                    self.tap(scroll_top_btn.box.center)
                    sleep(2)

                # Convert to English weekday
                weekday_name = self._date_to_english_weekday(date_name)
                logging.info(f"Converted date {date_name} to weekday {weekday_name}")

                # Scroll and scan the rankings for this date
                date_rankings = self._scan_rankings_for_current_date(
                    weekday_name, ocr_backend, fallback
                )
                date_rankings = self._correct_names_with_guild_members(
                    date_rankings, guild_members or []
                )
                rankings.extend(date_rankings)

                processed_dates.add(date_name)

                if len(processed_dates) >= dates_to_scan + 1:
                    break

    def _scan_rankings_for_current_date(
        self,
        date_name: str,
        ocr_backend: OCRBackend,
        fallback: OCRBackend | None = None,
        is_supreme_arena: bool = False,
    ) -> list[dict]:
        """Collect all (rank, name) observations, then canonicalize."""
        observations: list[tuple[str | None, str | None]] = []
        seen_ranks: set[str] = set()
        no_new_ranks_count = 0

        prefix = "sa" if is_supreme_arena else "dr"
        safe_date = re.sub(r"[^A-Za-z0-9_-]", "_", date_name)

        for scroll_idx in range(self._MAX_SCROLLS):
            screenshot = self.get_screenshot()
            self._save_debug_screenshot(
                screenshot, f"{prefix}_{safe_date}_{scroll_idx:03d}"
            )
            rows = self._parse_rankings_rows(
                screenshot,
                ocr_backend,
                fallback=fallback,
                is_first_frame=(scroll_idx == 0),
                is_supreme_arena=is_supreme_arena,
            )

            new_ranks_this_frame = False
            for raw_rank, name, score in rows:
                if not name:
                    continue
                rank = (raw_rank.lstrip("0") or raw_rank) if raw_rank else None
                observations.append((rank, name))
                if rank and rank not in seen_ranks:
                    seen_ranks.add(rank)
                    new_ranks_this_frame = True

            if new_ranks_this_frame:
                no_new_ranks_count = 0
            else:
                no_new_ranks_count += 1

            if no_new_ranks_count >= self._MAX_NEW_NAMES_NO_CHANGE:
                logging.info(
                    f"No new ranks for {self._MAX_NEW_NAMES_NO_CHANGE} "
                    f"consecutive scrolls. Finished date {date_name}."
                )
                break

            self.swipe_up(x=540, sy=1300, ey=1050, duration=1.2)
            sleep(2.5)

        return self._canonicalize_observations(observations, date_name)

    def _canonicalize_observations(
        self,
        observations: list[tuple[str | None, str | None]],
        date_name: str,
    ) -> list[dict]:
        """Group by rank, pick best name per player via frequency consensus."""
        rank_groups: dict[str, list[str]] = {}
        unranked: list[str] = []

        for rank, name in observations:
            if not name:
                continue
            if rank:
                rank_groups.setdefault(rank, []).append(name)
            else:
                unranked.append(name)

        results: list[dict] = []
        canonical_names: set[str] = set()

        # Sort rank groups: highest agreement ratio first (most self-consistent
        # readings = most reliable), then most observations, then rank number.
        # This ensures a clean rank "91" group beats a phantom "1" group that
        # has mixed names.
        def _agreement(r: str) -> float:
            names = rank_groups[r]
            if not names:
                return 0.0
            top = Counter(n.lower() for n in names).most_common(1)[0][1]
            return top / len(names)

        def _rank_sort_key(r: str) -> tuple:
            num = int(r) if r.isdigit() else 9999
            return (-_agreement(r), -len(rank_groups[r]), num)

        for rank in sorted(rank_groups, key=_rank_sort_key):
            names = rank_groups[rank]
            canonical = self._pick_canonical_name(names)
            if not canonical:
                continue
            if self._find_fuzzy_match(canonical, canonical_names) is not None:
                # Top pick is already canonical at another rank (hallucination
                # duplicate). Try the remaining candidates so we don't silently
                # drop the legitimate player displaced by the hallucination.
                # Guard: only include a candidate whose home rank IS this rank
                # (i.e. it appears at least as often here as anywhere else).
                # Without the guard, a player that belongs at rank R could be
                # incorrectly assigned to rank R-N (one hallucination) and then
                # missed at rank R when processed later.
                alt_names = [
                    n
                    for n in names
                    if self._find_fuzzy_match(n, canonical_names) is None
                    and not self._name_appears_more_elsewhere(n, rank, rank_groups)
                ]
                canonical = self._pick_canonical_name(alt_names)
                if not canonical:
                    logging.debug(
                        f"Rank {rank}: top candidate already covered, "
                        "no valid alternative found, skipping."
                    )
                    continue
                logging.debug(
                    f"Rank {rank}: top candidate already covered, "
                    f"using alternative {canonical!a}."
                )
            canonical_names.add(canonical)
            results.append({"Date": date_name, "Rank": rank, "Name": canonical})

        for group in self._group_by_similarity(unranked):
            if len(group) < self._MIN_UNRANKED_OBSERVATIONS:
                continue
            canonical = self._pick_canonical_name(group)
            if not canonical:
                continue
            if self._find_fuzzy_match(canonical, canonical_names) is not None:
                continue
            canonical_names.add(canonical)
            results.append({"Date": date_name, "Rank": "", "Name": canonical})

        results.sort(
            key=lambda e: int(e["Rank"]) if e["Rank"].isdigit() else float("inf")
        )
        logging.info(f"Canonicalized {len(results)} entries for {date_name}.")
        return results

    def _group_by_similarity(self, names: list[str]) -> list[list[str]]:
        """Cluster names into groups where each pair is fuzzy-similar."""
        groups: list[list[str]] = []
        for name in names:
            placed = False
            for group in groups:
                if (
                    SequenceMatcher(None, name.lower(), group[0].lower()).ratio()
                    >= self._FUZZY_DEDUP_THRESHOLD
                ):
                    group.append(name)
                    placed = True
                    break
            if not placed:
                groups.append([name])
        return groups

    def _pick_canonical_name(self, names: list[str]) -> str | None:
        """Return best name from OCR observations: most frequent fuzzy cluster wins."""
        quality = [
            n
            for n in names
            if n
            and len(n) >= self._MIN_NAME_LENGTH
            and sum(1 for c in n if c.isalnum()) / len(n) >= self._MIN_NAME_ALNUM_RATIO
        ]
        if not quality:
            return None

        # Largest fuzzy-similarity cluster = most frequently observed variant
        best_group = max(self._group_by_similarity(quality), key=len)

        # Within the cluster: most frequent exact form wins; break ties by quality
        counts = Counter(n.lower() for n in best_group)
        max_count = counts.most_common(1)[0][1]
        top = [n for n in best_group if counts[n.lower()] == max_count]

        return min(
            top,
            key=lambda n: (
                -sum(1 for c in n if c.isalnum()) / len(n),
                len(n),
            ),
        )

    def _name_appears_more_elsewhere(
        self,
        name: str,
        rank: str,
        rank_groups: dict[str, list[str]],
    ) -> bool:
        """Return True if `name` has more observations at any rank other than `rank`.

        Used to exclude alt candidates that truly belong at a different rank —
        e.g. a player seen once at rank 15 (hallucination) but five times at
        rank 25 (correct) should NOT be used as the alt at rank 15.
        """
        name_lower = name.lower()
        count_here = sum(
            1 for n in rank_groups.get(rank, []) if n.lower() == name_lower
        )
        return any(
            sum(1 for n in v if n.lower() == name_lower) > count_here
            for r, v in rank_groups.items()
            if r != rank
        )

    def _find_fuzzy_match(self, name: str, seen_names: set[str]) -> str | None:
        """Return the matched seen name if similar to `name`, else None."""
        name_lower = name.lower()
        for seen in seen_names:
            ratio = SequenceMatcher(None, name_lower, seen.lower()).ratio()
            if ratio >= self._FUZZY_DEDUP_THRESHOLD:
                return seen
        return None

    def _fetch_guild_members(self) -> list[str]:
        """Fetch guild member names from the configured API URL for name correction."""
        url = self.settings.guild_manager_scan.guild_members_api_url
        if not url:
            return []
        try:
            req = urllib.request.Request(url)
            parsed = urlparse(url)
            apikey = parse_qs(parsed.query).get("apikey", [""])[0]
            if apikey:
                req.add_header("apikey", apikey)
            req.add_header("Cache-Control", "no-cache")
            req.add_header("Pragma", "no-cache")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list) and "state" in data[0]:
                names = [
                    p["name"]
                    for p in data[0]["state"].get("players", [])
                    if p.get("name")
                ]
                logging.info(f"Fetched {len(names)} guild members for name correction.")
                return names
        except Exception as e:
            logging.warning(f"Could not fetch guild members: {e}")
        return []

    def _clean_member_name(self, name: str, suffix_pat: re.Pattern) -> str:
        """Clean a name by removing suffix codes and noise words."""
        cleaned = suffix_pat.sub("", name.lower())
        name_clean = "".join(c for c in cleaned if c.isalnum() or c.isspace())
        words = []
        for w in name_clean.split():
            if (
                len(w) > 1
                or not w.isalpha()
                or any(ord(c) > self._MAX_ASCII_VAL for c in w)
            ):
                words.append(w)
        return "".join(words)

    def _to_visual_latin(self, text: str) -> str:
        """Map Cyrillic characters to visually similar Latin homoglyphs."""
        mapping = {
            "\u0430": "a",
            "\u0431": "6",
            "\u0432": "b",
            "\u0433": "r",
            "\u0434": "g",
            "\u0435": "e",
            "\u0451": "e",
            "\u0436": "k",
            "\u0437": "3",
            "\u0438": "u",
            "\u0439": "u",
            "\u043a": "k",
            "\u043b": "n",
            "\u043c": "m",
            "\u043d": "h",
            "\u043e": "o",
            "\u043f": "n",
            "\u0440": "p",
            "\u0441": "c",
            "\u0442": "m",
            "\u0443": "y",
            "\u0444": "o",
            "\u0445": "x",
            "\u0446": "u",
            "\u0447": "u",
            "\u0448": "w",
            "\u0449": "w",
            "\u044a": "b",
            "\u044b": "bi",
            "\u044c": "b",
            "\u044d": "3",
            "\u044e": "io",
            "\u044f": "r",
            "\u0410": "A",
            "\u0411": "6",
            "\u0412": "B",
            "\u0413": "R",
            "\u0414": "G",
            "\u0415": "E",
            "\u0401": "E",
            "\u0416": "K",
            "\u0417": "3",
            "\u0418": "U",
            "\u0419": "U",
            "\u041a": "K",
            "\u041b": "N",
            "\u041c": "M",
            "\u041d": "H",
            "\u041e": "O",
            "\u041f": "N",
            "\u0420": "P",
            "\u0421": "C",
            "\u0422": "M",
            "\u0423": "Y",
            "\u0425": "X",
            "\u0426": "U",
            "\u0427": "U",
            "\u0428": "W",
            "\u0429": "W",
            "\u042b": "Bi",
            "\u042f": "R",
        }
        return "".join(mapping.get(c, c) for c in text)

    def _strip_diacritics(self, text: str) -> str:
        """Replace non-ASCII diacritics with their base ASCII equivalents."""
        import unicodedata  # noqa: PLC0415

        _map = {
            "ø": "o",
            "Ø": "O",
            "ą": "a",
            "Ą": "A",
            "ę": "e",
            "Ę": "E",
            "ś": "s",
            "Ś": "S",
            "ź": "z",
            "Ź": "Z",
            "ż": "z",
            "Ż": "Z",
            "ł": "l",
            "Ł": "L",
            "æ": "ae",
            "Æ": "AE",
            "þ": "th",
            "Þ": "TH",
            "ß": "ss",
        }
        result = []
        for c in text:
            mapped = _map.get(c)
            if mapped is not None:
                result.append(mapped)
                continue
            nfd = unicodedata.normalize("NFD", c)
            ascii_base = nfd.encode("ascii", "ignore").decode("ascii")
            result.append(ascii_base if ascii_base else c)
        return "".join(result)

    def _find_best_member_match(
        self,
        name: str,
        cleaned_members: list[tuple[str, str]],
        suffix_pat: re.Pattern,
    ) -> tuple[str, float]:
        """Find the closest guild member match and returns (best_match, ratio)."""
        name_clean = self._clean_member_name(name, suffix_pat)
        # Identify Korean (Hangul) members in the guild list.
        # RapidOCR often garbles Korean into CJK/Chinese characters.
        # When OCR output is Korean or a CJK misread, restrict matching to
        # Hangul members only (fuzzy-ranked). This generalises to any number
        # of Hangul members (JP/KR/mixed guilds).
        _hangul_pat = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
        korean_members = [m for m, _ in cleaned_members if _hangul_pat.search(m)]
        if korean_members:
            is_korean = bool(_hangul_pat.search(name))
            is_misread = name_clean in ("号1o", "号10", "号10g", "号1og", "号lo")
            _cjk_pat = re.compile(r"[一-鿿぀-ヿ豈-﫿]")
            is_cjk_misread = bool(_cjk_pat.search(name_clean)) and not any(
                name_clean == mc for _, mc in cleaned_members if _cjk_pat.search(mc)
            )
            if is_korean or is_cjk_misread or is_misread:
                if len(korean_members) == 1:
                    return korean_members[0], 1.0
                # Multiple Hangul members: pick the best fuzzy match.
                # For CJK misreads the ratio will be low for all; we still
                # return the closest one with enough confidence to clear the
                # _GUILD_NAME_CORRECTION_THRESHOLD (0.65).
                best_k, best_k_ratio = korean_members[0], 0.0
                for km in korean_members:
                    kmc = self._clean_member_name(km, suffix_pat)
                    r = SequenceMatcher(None, name_clean, kmc).ratio()
                    if r > best_k_ratio:
                        best_k_ratio, best_k = r, km
                return best_k, max(best_k_ratio, 0.7)

        if not name_clean:
            return name, 0.0

        # Strip Latin diacritics not handled by visual_latin (e.g. ø→o, ą→a)
        name_clean = self._strip_diacritics(name_clean)

        # Convert to visual Latin to support Cyrillic homoglyph matching
        name_visual = self._to_visual_latin(name_clean)

        best_ratio = 0.0
        best_match = name

        for member, member_clean in cleaned_members:
            member_visual = self._to_visual_latin(self._strip_diacritics(member_clean))
            if name_visual == member_visual:
                return member, 1.0

            ratio = SequenceMatcher(None, name_visual, member_visual).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = member

        return best_match, best_ratio

    def _correct_names_with_guild_members(
        self, rankings: list[dict], guild_members: list[str]
    ) -> list[dict]:
        """Replace OCR-misread names with the closest matching guild member name."""
        if not guild_members:
            return rankings

        suffix_pat = re.compile(r"\b[A-Za-z]?\d{3,4}\b")

        # Pre-clean the master list of guild members for faster comparison
        cleaned_members = [
            (m, self._clean_member_name(m, suffix_pat)) for m in guild_members
        ]

        corrected_entries: list[dict] = []

        for entry in rankings:
            name = entry["Name"]
            best_match, best_ratio = self._find_best_member_match(
                name, cleaned_members, suffix_pat
            )

            if best_ratio >= self._GUILD_NAME_CORRECTION_THRESHOLD:
                if best_match != name:
                    logging.debug(
                        f"Name corrected: {name!a} -> {best_match!a} ({best_ratio:.2f})"
                    )
                new_entry = entry.copy()
                new_entry["Name"] = best_match
                new_entry["_match_ratio"] = best_ratio
                corrected_entries.append(new_entry)
            else:
                logging.debug(
                    f"Name discarded as non-guild member noise: {name!a} "
                    f"(best: {best_match!a}, ratio: {best_ratio:.2f})"
                )

        # Deduplicate by (Date, Name) keeping the highest match ratio
        dedup_dict: dict[tuple[str, str], dict] = {}
        for entry in corrected_entries:
            key = (entry.get("Date", ""), entry["Name"])
            existing = dedup_dict.get(key)
            if not existing:
                dedup_dict[key] = entry
                continue

            curr_ratio = entry["_match_ratio"]
            ex_ratio = existing["_match_ratio"]
            if curr_ratio > ex_ratio:
                dedup_dict[key] = entry
            elif (
                curr_ratio == ex_ratio
                and entry.get("Rank")
                and not existing.get("Rank")
            ):
                dedup_dict[key] = entry

        # Clean up temporary field and convert back to list
        final_rankings = []
        for entry in dedup_dict.values():
            entry.pop("_match_ratio", None)
            final_rankings.append(entry)

        # Re-sort final rankings by Rank (numeric)
        def _get_rank_key(e: dict) -> float:
            r = e.get("Rank", "")
            return int(r) if r.isdigit() else float("inf")

        final_rankings.sort(key=_get_rank_key)

        return final_rankings

    def _save_rankings_to_json(self, rankings: list[dict]) -> None:
        if not rankings:
            logging.warning("No rankings data collected.")
            return

        try:
            data_root = SettingsLoader.get_app_config_dir()
            output_dir = data_root / "data"
            os.makedirs(output_dir, exist_ok=True)
            output_file = output_dir / "dream_realm_rankings.json"

            with open(output_file, mode="w", encoding="utf-8") as f:
                json.dump(rankings, f, indent=4, ensure_ascii=False)

            logging.info(f"Successfully exported {len(rankings)} ranking entries.")
            logging.info(f"Output file path: {output_file}")
        except Exception as e:
            logging.error(f"Failed to save rankings JSON: {e}")

    def _date_to_english_weekday(self, date_str: str) -> str:
        """Convert MM/DD date string to English weekday name."""
        digits = re.findall(r"\d+", date_str)
        if len(digits) != self._EXPECTED_DATE_PARTS:
            return date_str

        try:
            month = int(digits[0])
            day = int(digits[1])
            current_year = datetime.datetime.now().year
            d = datetime.date(current_year, month, day)

            # Handle year boundary (e.g. today is Jan 2027, date tab is 12/31)
            today = datetime.date.today()
            if d > today:
                d = datetime.date(current_year - 1, month, day)

            weekdays = {
                0: "Monday",
                1: "Tuesday",
                2: "Wednesday",
                3: "Thursday",
                4: "Friday",
                5: "Saturday",
                6: "Sunday",
            }
            return weekdays[d.weekday()]
        except ValueError:
            return date_str

    def _is_date_string(self, text: str) -> bool:
        text = text.strip()
        if len(text) > self._MAX_DATE_LEN:
            return False
        # Matches format "MM/DD", "MM-DD", "MM.DD"
        if re.match(r"^\d{1,2}[\./-]\d{1,2}$", text):
            return True
        lower_text = text.lower()
        months = [
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
            "day",
        ]
        if any(m in lower_text for m in months) and any(
            c.isdigit() for c in lower_text
        ):
            return True
        return False

    def _select_district_rankings(self, ocr_backend: OCRBackend) -> bool:
        logging.info("Selecting District Rankings tab...")
        for _ in range(5):
            screenshot = self.get_screenshot()
            ocr_results = ocr_backend.detect_text_blocks(screenshot)
            for res in ocr_results:
                text = res.text.lower()
                y = res.box.center.y
                if y > self._Y_TAB_MIN and "district" in text:
                    logging.info(
                        f"Found District Rankings tab at {res.box.center}, tapping."
                    )
                    self.tap(res.box.center)
                    self.sleep_action()
                    return True
            sleep(1)
        return False

    def _find_date_tabs(self, ocr_backend: OCRBackend) -> list[OCRResult]:
        logging.info("Searching for date tabs...")
        screenshot = self.get_screenshot()
        ocr_results = ocr_backend.detect_text_blocks(screenshot)

        date_tabs = []
        for res in ocr_results:
            y = res.box.center.y
            if self._Y_MIN_DATE <= y <= self._Y_MAX_DATE:
                if self._is_date_string(res.text):
                    # Filter out date tabs that are partially cut off at screen edges
                    if (
                        res.box.left >= self._X_MIN_DATE_TAB
                        and res.box.right <= self._X_MAX_DATE_TAB
                    ):
                        date_tabs.append(res)
                    else:
                        logging.debug(
                            f"Ignoring date tab '{res.text}' because it is "
                            f"partially cut off (left={res.box.left}, "
                            f"right={res.box.right})."
                        )

        # Group by Y coordinate to find the row of date tabs
        y_groups = []
        for res in date_tabs:
            added = False
            for group in y_groups:
                if (
                    abs(group[0].box.center.y - res.box.center.y)
                    < self._Y_DATE_ALIGNMENT_TOLERANCE
                ):
                    group.append(res)
                    added = True
                    break
            if not added:
                y_groups.append([res])

        if y_groups:
            best_group = max(y_groups, key=len)
            date_tabs = sorted(best_group, key=lambda r: r.box.center.x)

        logging.info(f"Found {len(date_tabs)} date tabs: {[r.text for r in date_tabs]}")
        return date_tabs

    def _is_guild_members_option(self, text: str) -> bool:
        text_lower = text.lower()
        if "guild" not in text_lower:
            return False
        # Avoid matching player cards containing "Not in a Guild"
        if "not" in text_lower:
            return False
        return True

    def _set_guild_members_filter(self, ocr_backend: OCRBackend) -> bool:
        logging.info("Setting filter to Guild Members...")

        # 1. Try to find the filter button using template matching
        filter_btn = self.game_find_template_match(
            "dream_realm/filter.png", threshold=ConfidenceValue("80%")
        )

        if filter_btn:
            logging.info(
                "Found filter button using template match at "
                f"{filter_btn.box.center}, tapping."
            )
            self.tap(filter_btn.box.center)
        else:
            logging.warning("Filter template not found, falling back to OCR.")
            screenshot = self.get_screenshot()
            ocr_results = ocr_backend.detect_text_blocks(screenshot)
            filter_keywords = ["all", "server", "district", "guild"]
            fallback_btn = None
            for res in ocr_results:
                text = res.text.lower()
                # Exclude the actual "Guild Members" dropdown text or "Not in a Guild"
                if any(
                    kw in text for kw in filter_keywords
                ) and not self._is_guild_members_option(res.text):
                    fallback_btn = res
                    break

            if fallback_btn:
                logging.info(
                    "Found fallback filter button at "
                    f"{fallback_btn.box.center}, tapping."
                )
                self.tap(fallback_btn.box.center)
            else:
                logging.error("Could not locate filter button on screen.")
                return False

        self.sleep_action()
        sleep(1.5)

        # 2. Look for "Guild Members" in the opened dropdown
        for _ in range(3):
            screenshot = self.get_screenshot()
            ocr_results = ocr_backend.detect_text_blocks(screenshot)
            for res in ocr_results:
                if self._is_guild_members_option(res.text):
                    logging.info(
                        f"Found Guild Members option '{res.text}' "
                        f"at {res.box.center}, tapping."
                    )
                    self.tap(res.box.center)
                    self.sleep_action()
                    sleep(1.5)
                    return True
            sleep(1)

        logging.warning("Could not find Guild Members option in filter dropdown.")
        return False

    def _parse_rankings_rows(
        self,
        screenshot,
        ocr_backend: OCRBackend,
        fallback: OCRBackend | None = None,
        is_first_frame: bool = False,
        is_supreme_arena: bool = False,
    ) -> list[tuple[str | None, str | None, str | None]]:
        # Determine the valid Y scan region (same logic for both paths)
        y_min = self._Y_MIN_RANKINGS
        if is_supreme_arena:
            # The SA podium (decorative top-3 display) ends at ~y=600 and is
            # present in ALL frames. Always crop at y=700 so neither bbox nor
            # Qwen ever sees the podium rank badges ("1"/"2"/"3") regardless of
            # whether the guild's top players match the global top-3.
            y_min = 700
        elif is_first_frame:
            y_min = 820  # Exclude the District podium in Dream Realm

        # --- Qwen2-VL path: structured extraction on the cropped region ---
        if isinstance(ocr_backend, QwenVLOCRBackend):
            h = screenshot.shape[0]
            backend_name = "qwen2vl"
            # SA first frame: Qwen uses y=700 (same as bbox) — no podium visible.
            # SA/DR non-first: Qwen uses y=350 for maximum context. The larger
            #   crop prevents Qwen from entering "Cyrillic mode" (reading Latin
            #   names as Russian transliterations, e.g. "Aroshard" → "Арошард")
            #   that occurs when only the score column is visible at y=700.
            #   Podium hallucinations (ranks 1/2/3 in non-first frames) are
            #   stripped downstream by the bbox_rank_set filter.
            # DR first frame: cut artistic header only (y=450); list from y~820.
            llm_y_min = (
                y_min
                if is_supreme_arena and is_first_frame
                else 450
                if is_first_frame
                else 350
            )
            scan_region = screenshot[llm_y_min : min(h, self._Y_MAX_RANKINGS), :]
            rows = ocr_backend.extract_rankings_from_screenshot(scan_region)
            if rows is not None:
                guild_set: set[str] = {
                    re.sub(r"\s*[A-Za-z]\d{3,4}\s*$", "", m).strip()
                    for m in (getattr(self, "_guild_members", None) or [])
                }
                # Discard Cyrillic-mode hallucinations: names containing
                # Cyrillic characters that are not actual guild members
                # (e.g. "Арошард" for "Aroshard", "Персефоне" for "Persephone").
                # This occurs when Qwen sees only the score column (insufficient
                # English context) and falls into Russian transliteration mode.
                guild_lower = {n.lower() for n in guild_set}
                rows = [
                    (rk, nm, sc)
                    for rk, nm, sc in rows
                    if not (
                        nm
                        and any("Ѐ" <= c <= "ӿ" for c in nm)
                        and nm.lower() not in guild_lower
                    )
                ]
                # Supplement with bounding-box OCR for any guild members the
                # LLM missed (e.g. dark/silhouette avatars). Added 3x so they
                # outweigh LLM hallucinations in the canonicalization vote.
                # Use (rank, name) tuples so bbox can correct rank shifts (e.g.
                # Sebv at rank 44 vs correct rank 49) without being blocked.
                llm_rank_names: set[tuple[str | None, str]] = {
                    (rk, n) for rk, n, _ in rows if n
                }
                if not hasattr(self, "_rapidocr_supplement"):
                    self._rapidocr_supplement = RapidOCRBackend()
                bbox_rows, bbox_debug, bbox_ocr_all = self._parse_rankings_bbox(
                    screenshot, self._rapidocr_supplement, y_min, is_supreme_arena
                )
                rows = self._apply_bbox_rank_corrections(
                    rows, bbox_rows, is_supreme_arena, is_first_frame
                )
                llm_rank_names = {(rk, n) for rk, n, _ in rows if n}
                supplemental = [
                    r
                    for r in bbox_rows
                    if r[1] and (r[0], r[1]) not in llm_rank_names and r[1] in guild_set
                ]
                # SA non-first: bbox null-rank supplementals accumulate
                # x3 votes per frame and can outvote a correct Qwen reading
                # from frame 0 (e.g. Sebv=7 from Qwen loses to 6x null-rank
                # supplement votes). Only keep supplemental entries that bbox
                # confirmed with an actual rank number.
                if is_supreme_arena and not is_first_frame:
                    supplemental = [r for r in supplemental if r[0] is not None]

                # Qwen row-crop recovery for names bbox misread as Latin
                # (e.g. ОпасныйПоцык rendered in game font → OnacHbINlo1IbIK).
                qwen_recovered = self._recover_supplement_names_qwen(
                    screenshot, bbox_debug, guild_set, supplemental, ocr_backend
                )

                if self._ocr_debug is not None:
                    in_range = [
                        b
                        for b in bbox_ocr_all
                        if y_min <= b.box.center.y <= self._Y_MAX_RANKINGS
                    ]
                    self._ocr_debug.append(
                        {
                            "backend": backend_name,
                            "is_supreme_arena": is_supreme_arena,
                            "is_first_frame": is_first_frame,
                            "y_min": llm_y_min,
                            "bbox_y_min": y_min,
                            "bbox_raw_total": len(bbox_ocr_all),
                            "bbox_in_range": len(in_range),
                            "bbox_y_sample": [
                                {"text": b.text, "cy": b.box.center.y}
                                for b in sorted(
                                    bbox_ocr_all, key=lambda b: b.box.center.y
                                )[:8]
                            ],
                            "rows": [
                                {"rank": r, "name": n, "score": s} for r, n, s in rows
                            ],
                            "bbox_supplement": bbox_debug,
                            "supplemental_added": [
                                {"rank": r, "name": n} for r, n, _ in supplemental
                            ],
                            "qwen_row_recovered": qwen_recovered,
                        }
                    )
                return rows + supplemental * 3
            logging.debug(
                f"{backend_name} failed for this frame — falling back to RapidOCR."
            )
            if not hasattr(self, "_rapidocr_supplement"):
                self._rapidocr_supplement = RapidOCRBackend()
            ocr_backend = self._rapidocr_supplement

        # --- Bounding-box path (RapidOCR) ---
        parsed_rows, debug_rows, ocr_results = self._parse_rankings_bbox(
            screenshot, ocr_backend, y_min, is_supreme_arena
        )

        if self._ocr_debug is not None:
            self._ocr_debug.append(
                {
                    "is_supreme_arena": is_supreme_arena,
                    "is_first_frame": is_first_frame,
                    "y_min": y_min,
                    "all_ocr_blocks": [
                        {"text": b.text, "cx": b.box.center.x, "cy": b.box.center.y}
                        for b in ocr_results
                    ],
                    "rows": debug_rows,
                }
            )

        return parsed_rows

    def _apply_bbox_rank_corrections(
        self,
        rows: list[tuple],
        bbox_rows: list[tuple],
        is_supreme_arena: bool,
        is_first_frame: bool,
    ) -> list[tuple]:
        """Correct Qwen rank misreads and strip podium hallucinations.

        Strategy 1: bbox found the same name at a different rank → trust bbox.
        Strategy 2: bbox has nothing at rank N but an empty slot at N+1 →
          Qwen was off-by-one (non-guild member at N pushed names down).
        Non-first filter: when bbox has data, keep only rows whose rank is
          confirmed by bbox — removes podium hallucinations (ranks 1/2/3 seen
          in all frames) and Qwen rank misreads (e.g. ОпасныйПоцык=24 where
          bbox confirms the real rank is 29). Guard: if bbox returned nothing,
          skip the filter to avoid discarding all Qwen readings.
        """
        rank_set = {r for r, _, _ in bbox_rows if r}
        name_rank = {n: r for r, n, _ in bbox_rows if n and r}
        empty_ranks = {r for r, n, _ in bbox_rows if r and not n}
        corrected = []
        for rank_q, name_q, score_q in rows:
            fixed_rank = rank_q
            if name_q and rank_q and rank_q.isdigit():
                if name_q in name_rank and name_rank[name_q] != rank_q:
                    fixed_rank = name_rank[name_q]
                elif rank_q not in rank_set and str(int(rank_q) + 1) in empty_ranks:
                    fixed_rank = str(int(rank_q) + 1)
            corrected.append((fixed_rank, name_q, score_q))
        if not is_first_frame and rank_set:
            # SA podium (ranks 1/2/3) is always visible — those are the true
            # hallucinations.  For any other rank, if Qwen read a confirmed
            # guild-member name there and bbox simply missed that row (dark
            # avatar, OCR blind-spot), keep the entry so the member isn't lost.
            _podium_ranks = {"1", "2", "3"}
            guild_names: set[str] = {
                re.sub(r"\s*[A-Za-z]\d{3,4}\s*$", "", m).strip()
                for m in (getattr(self, "_guild_members", None) or [])
            }
            corrected = [
                (rk, nm, sc)
                for rk, nm, sc in corrected
                if rk
                and (
                    rk in rank_set
                    or (nm and nm in guild_names and rk not in _podium_ranks)
                )
            ]
        # Deduplicate by rank: if Qwen assigns the same rank to two players
        # (e.g. Night=5 and Sebv=5 when Sebv is actually rank 7), prefer the
        # bbox-confirmed name; otherwise keep the first occurrence in list order.
        seen_ranks: dict[str, tuple] = {}
        deduped: list[tuple] = []
        for rk, nm, sc in corrected:
            if not rk or rk not in seen_ranks:
                deduped.append((rk, nm, sc))
                if rk:
                    seen_ranks[rk] = (rk, nm, sc)
            elif nm and nm in name_rank:
                # This name is bbox-confirmed at this rank — replace the
                # earlier (unconfirmed) occupant.
                idx = next(i for i, t in enumerate(deduped) if t[0] == rk)
                deduped[idx] = (rk, nm, sc)
                seen_ranks[rk] = (rk, nm, sc)
        return deduped

    def _recover_supplement_names_qwen(
        self,
        screenshot,
        bbox_debug: list[dict],
        guild_set: set[str],
        supplemental: list,
        ocr_backend: QwenVLOCRBackend,
        max_recovery: int = 3,
    ) -> list[dict]:
        """Crop each bbox row whose name isn't in guild_set and ask Qwen.

        Handles members whose name the game font renders as Latin lookalikes
        (e.g. ОпасныйПоцык → OnacHbINlo1IbIK). Returns a list of recovered
        entries for debug logging.
        """
        recovered_set: set[str] = {r[1] for r in supplemental if r[1]}
        qwen_recovered: list[dict] = []
        for entry in bbox_debug:
            if len(qwen_recovered) >= max_recovery:
                break
            bbox_name = entry.get("name")
            if not bbox_name or bbox_name in guild_set:
                continue
            entry_blocks = entry.get("blocks", [])
            if not entry_blocks:
                continue
            # Use only the topmost name_guild block for Y — avoids including
            # the guild-name row (CITADEL) which sits below the player name.
            name_blocks = [b for b in entry_blocks if b.get("col") == "name_guild"]
            ref_blocks = name_blocks if name_blocks else entry_blocks
            name_cy = min(b["cy"] for b in ref_blocks)
            name_row_half = 50
            crop = screenshot[
                max(0, name_cy - name_row_half) : min(
                    screenshot.shape[0], name_cy + name_row_half
                ),
                self._X_RANK_BOUNDARY : self._X_SCORE_BOUNDARY,
            ]
            recovered = ocr_backend.extract_player_name(crop)
            if not recovered:
                continue
            matched = next(
                (m for m in guild_set if m.lower() == recovered.lower()), None
            )
            if matched and matched not in recovered_set:
                rank_str = entry.get("rank")
                score_str = next(
                    (b["text"] for b in entry_blocks if b.get("col") == "score"),
                    None,
                )
                supplemental.append((rank_str, matched, score_str))
                recovered_set.add(matched)
                qwen_recovered.append({"rank": rank_str, "name": matched})
        return qwen_recovered

    def _parse_rankings_bbox(
        self,
        screenshot,
        ocr_backend: OCRBackend,
        y_min: int,
        is_supreme_arena: bool,
    ) -> tuple[
        list[tuple[str | None, str | None, str | None]],
        list[dict],
        list,
    ]:
        """Run the bounding-box OCR path.

        Returns (parsed_rows, debug_rows, ocr_results).
        """
        ocr_results = ocr_backend.detect_text_blocks(screenshot)

        row_blocks = [
            res
            for res in ocr_results
            if y_min <= res.box.center.y <= self._Y_MAX_RANKINGS
        ]
        row_blocks.sort(key=lambda r: r.box.center.y)

        rows_grouped: list[list] = []
        for res in row_blocks:
            for group in rows_grouped:
                if (
                    abs(group[0].box.center.y - res.box.center.y)
                    < self._Y_ROW_ALIGNMENT_TOLERANCE
                ):
                    group.append(res)
                    break
            else:
                rows_grouped.append([res])

        parsed_rows: list[tuple[str | None, str | None, str | None]] = []
        debug_rows: list[dict] = []
        for idx, row in enumerate(rows_grouped):
            row_sorted = sorted(row, key=lambda r: r.box.center.x)
            skipped_reason = self._row_skip_reason(row_sorted, is_supreme_arena)
            blocks_info = self._debug_blocks(row_sorted)
            if skipped_reason:
                debug_rows.append({"skipped": skipped_reason, "blocks": blocks_info})
                continue
            result = self._parse_single_row(row_sorted, screenshot, ocr_backend, idx)
            parsed_rows.append(result)
            debug_rows.append(
                {
                    "rank": result[0],
                    "name": result[1],
                    "score": result[2],
                    "blocks": blocks_info,
                }
            )

        return parsed_rows, debug_rows, ocr_results

    def _row_skip_reason(
        self, row_sorted: list[OCRResult], is_supreme_arena: bool
    ) -> str | None:
        if len(row_sorted) < self._MIN_ROW_BLOCKS:
            return f"too_few_blocks({len(row_sorted)})"
        if not is_supreme_arena and not any(
            b.box.center.x >= self._X_SCORE_BOUNDARY for b in row_sorted
        ):
            return "no_score_block"
        return None

    def _debug_blocks(self, row_sorted: list[OCRResult]) -> list[dict]:
        result = []
        for b in row_sorted:
            cx = b.box.center.x
            if cx < self._X_RANK_BOUNDARY:
                col = "rank"
            elif cx >= self._X_SCORE_BOUNDARY:
                col = "score"
            else:
                col = "name_guild"
            result.append({"text": b.text, "cx": cx, "cy": b.box.center.y, "col": col})
        return result

    def _classify_row_blocks(
        self, row_sorted: list[OCRResult]
    ) -> tuple[list[OCRResult], list[OCRResult], list[OCRResult]]:
        """Split row blocks into rank, name/guild, and score columns."""
        rank_blocks: list[OCRResult] = []
        name_guild_blocks: list[OCRResult] = []
        score_blocks: list[OCRResult] = []
        for block in row_sorted:
            x = block.box.center.x
            if x < self._X_RANK_BOUNDARY:
                rank_blocks.append(block)
            elif x < self._X_SCORE_BOUNDARY:
                name_guild_blocks.append(block)
            else:
                score_blocks.append(block)
        return rank_blocks, name_guild_blocks, score_blocks

    def _extract_rank_from_crop(
        self,
        screenshot,
        ocr_backend: OCRBackend,
        ref_y: int,
    ) -> str | None:
        """Crop the rank badge area near ref_y and OCR for digits."""
        h, w = screenshot.shape[:2]
        crop = screenshot[
            max(0, ref_y - 50) : min(h, ref_y + 50),
            50 : min(w, 190),
        ]
        if crop.size == 0:
            return None
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (0, 0), fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

        blocks = sorted(
            ocr_backend.detect_text_blocks(resized), key=lambda r: r.box.center.x
        )
        for block in blocks:
            digits = re.findall(r"\d+", block.text)
            if digits:
                return max(digits, key=len)
        return None

    def _extract_player_name(
        self,
        name_guild_blocks: list[OCRResult],
        valid_score_blocks: list[OCRResult],
        row_sorted: list[OCRResult],
    ) -> str | None:
        """Extract the player name, filtering out guild names by Y position."""
        if not name_guild_blocks:
            return None
        score_y = valid_score_blocks[0].box.center.y if valid_score_blocks else None
        # When there is no score block (e.g. Supreme Arena), measure Y offset
        # relative to the topmost block within name_guild_blocks only — not the
        # whole row — so that the rank badge Y doesn't skew the calculation.
        name_y_min = min(b.box.center.y for b in name_guild_blocks)
        valid = [
            b
            for b in name_guild_blocks
            if (
                b.box.center.y < score_y - 20
                if score_y is not None
                else (b.box.center.y - name_y_min < self._Y_GUILD_OFFSET)
            )
        ]
        if not valid:
            return None
        name = min(valid, key=lambda b: b.box.center.y).text.strip()
        name = re.sub(r"\s*[A-Za-z]\d{3,4}\s*$", "", name).strip()
        if not name or len(name) < self._MIN_NAME_LENGTH:
            return None
        if sum(1 for c in name if c.isalnum()) / len(name) < self._MIN_NAME_ALNUM_RATIO:
            return None
        return name

    def _parse_single_row(
        self,
        row_sorted: list[OCRResult],
        screenshot,
        ocr_backend: OCRBackend,
        row_index: int = -1,
    ) -> tuple[str | None, str | None, str | None]:
        rank_blocks, name_guild_blocks, score_blocks = self._classify_row_blocks(
            row_sorted
        )
        valid_score_blocks = [
            b for b in score_blocks if b.text.strip().lower() != "season"
        ]
        score = valid_score_blocks[0].text.strip() if valid_score_blocks else None

        rank = None
        if rank_blocks:
            # Only the leftmost block is the actual rank badge.  Blocks that OCR
            # places just inside the rank boundary are player names — move them
            # to name_guild_blocks so they aren't consumed by rank parsing.
            leftmost = min(rank_blocks, key=lambda b: b.box.center.x)
            spillover = [b for b in rank_blocks if b is not leftmost]
            name_guild_blocks = spillover + name_guild_blocks
            rank_digits = "".join(re.findall(r"\d", leftmost.text))
            if rank_digits and int(rank_digits) <= self._MAX_RANK_NUMBER:
                rank = rank_digits

        name = self._extract_player_name(
            name_guild_blocks, valid_score_blocks, row_sorted
        )
        if rank is None and name and row_sorted:
            ref_y = int(sum(b.box.center.y for b in row_sorted) / len(row_sorted))
            crop_rank = self._extract_rank_from_crop(screenshot, ocr_backend, ref_y)
            if crop_rank and int(crop_rank) <= self._MAX_RANK_NUMBER:
                rank = crop_rank

        return rank, name, score

    def _navigate_to_guild_hall(self, ocr_backend: OCRBackend) -> bool:
        """Tap the Guild tab in the bottom nav and wait for the hall view to load.

        Returns True if the Guild Hall is reached, False if the tab is not found.
        """
        screenshot = self.get_screenshot()
        ocr_results = ocr_backend.detect_text_blocks(screenshot)
        guild_tab = next(
            (
                r
                for r in ocr_results
                if r.text.strip().lower() == "guild"
                and self._Y_GUILD_NAV_MIN <= r.box.center.y <= self._Y_GUILD_NAV_MAX
            ),
            None,
        )
        if guild_tab is None:
            logging.warning(
                "Could not find Guild tab in bottom navigation bar. "
                "Trying navigate_to_world first."
            )
            self.navigate_to_world()
            sleep(2)
            screenshot = self.get_screenshot()
            ocr_results = ocr_backend.detect_text_blocks(screenshot)
            guild_tab = next(
                (
                    r
                    for r in ocr_results
                    if r.text.strip().lower() == "guild"
                    and self._Y_GUILD_NAV_MIN <= r.box.center.y <= self._Y_GUILD_NAV_MAX
                ),
                None,
            )
        if guild_tab is None:
            logging.error("Guild tab not found.")
            return False
        logging.info(f"Tapping Guild tab at {guild_tab.box.center}.")
        self.tap(guild_tab.box.center)
        sleep(2.5)
        return True

    def _navigate_to_guild_members_screen(self, ocr_backend: OCRBackend) -> bool:
        """Navigate to the Guild Members list screen.

        1. Tap the 'Guild' tab in the bottom navigation bar (detected by OCR).
        2. Wait for the guild hall view to load.
        3. Swipe to reveal the hidden 'Members' button.
        4. Tap 'Members'.

        Returns True if successfully reached the Members screen, False otherwise.
        """
        logging.info("Navigating to Guild Members screen...")

        if not self._navigate_to_guild_hall(ocr_backend):
            logging.error("Guild tab not found. Cannot navigate to Guild Members.")
            return False

        # Step 2: swipe to reveal the Members button
        logging.info("Swiping to reveal Members button...")
        self.device.swipe(
            Point(self._GUILD_SWIPE_SX, self._GUILD_SWIPE_SY),
            Point(self._GUILD_SWIPE_EX, self._GUILD_SWIPE_EY),
            duration=0.6,
        )
        sleep(1.5)

        # Step 3: find and tap Members via OCR
        for attempt in range(3):
            screenshot = self.get_screenshot()
            ocr_results = ocr_backend.detect_text_blocks(screenshot)
            members_btn = None
            for res in ocr_results:
                if "member" in res.text.strip().lower():
                    members_btn = res
                    break

            if members_btn is not None:
                logging.info(
                    f"Found Members button at {members_btn.box.center}, tapping."
                )
                self.tap(members_btn.box.center)
                sleep(2)
                return True

            if attempt < self._GUILD_NAV_SWIPE_MAX_ATTEMPTS:
                # Additional swipe in case the first one wasn't enough
                logging.warning("Members button not found, swiping again to reveal it.")
                self.device.swipe(
                    Point(self._GUILD_SWIPE_SX, self._GUILD_SWIPE_SY),
                    Point(self._GUILD_SWIPE_EX, self._GUILD_SWIPE_EY),
                    duration=0.6,
                )
                sleep(1.5)

        logging.error("Members button not found after multiple attempts.")
        return False

    # Regex that identifies non-name OCR blocks (power ratings, UI labels, etc.)
    _RE_POWER_RATING = re.compile(
        r"^\d+[.,]?\d*\s*[KMBkmb]\b",  # e.g. "108M", "81640K"
        re.IGNORECASE,
    )
    # Match (Base) with standard or full-width parentheses (U+FF08 / U+FF09)
    _RE_BASE_SUFFIX = re.compile(
        r"[(" + chr(0xFF08) + r"]\s*[Bb]ase\s*[)" + chr(0xFF09) + r"]"
    )
    _RE_GUILD_HEADER = re.compile(
        r"guild\s*member",
        re.IGNORECASE,
    )
    # Max digit count for a purely-numeric player name (e.g. "67" is 2 digits)
    _MAX_NUMERIC_NAME_DIGITS = 4

    def _is_valid_activeness_name(self, text: str) -> bool:
        """Return True only when `text` looks like a real player name."""
        t = text.strip()
        if len(t) < self._MIN_NAME_LENGTH:
            return False
        # Reject power-rating values like "108M (Base)", "81640K(Base)"
        if self._RE_POWER_RATING.match(t) or self._RE_BASE_SUFFIX.search(t):
            return False
        # Reject guild/UI header labels
        if self._RE_GUILD_HEADER.search(t):
            return False
        # Purely-numeric strings: reject large numbers (likely activeness values
        # bleeding into the name column), but allow short ones (e.g. player named "67").
        digits_only = t.replace(",", "").replace(".", "")
        if digits_only.isdigit() and int(digits_only) >= self._MIN_ACTIVENESS_VALUE:
            if len(digits_only) > self._MAX_NUMERIC_NAME_DIGITS:
                return False
        return True

    def _parse_activeness_rows(
        self,
        screenshot,
        ocr_backend: OCRBackend,
        frame_label: str | None = None,
    ) -> list[tuple[str | None, str | None]]:
        """Parse (name, activeness_value) pairs from the guild members list screen.

        Strategy
        --------
        1. Collect every valid name block in the left column (x < _X_ACTIVENESS_MIN).
        2. For each name, search for the nearest numeric activeness block on the right
           (x >= _X_ACTIVENESS_MIN) within _Y_ACTIVENESS_PAIR_RADIUS pixels.
        3. If no activeness block is found for a name (e.g. after a weekly reset when
           a member has 0 activeness and the game shows no number), report activeness=0
           so the member is still included in the output.
        """
        ocr_results = ocr_backend.detect_text_blocks(screenshot)

        # Filter to member list area
        area_blocks = [
            res
            for res in ocr_results
            if self._Y_ACTIVENESS_MIN <= res.box.center.y <= self._Y_ACTIVENESS_MAX
        ]

        # Separate activeness numbers (right column) from name blocks (left column)
        activeness_blocks = []
        name_blocks = []
        for b in area_blocks:
            t = b.text.strip()
            if (
                t.isdigit()
                and b.box.center.x >= self._X_ACTIVENESS_MIN
                and self._MIN_ACTIVENESS_VALUE <= int(t) <= self._MAX_ACTIVENESS_VALUE
            ):
                activeness_blocks.append(b)
            elif (
                self._is_valid_activeness_name(t)
                and b.box.center.x < self._X_ACTIVENESS_MIN
            ):
                name_blocks.append(b)

        # Sort name blocks top-to-bottom; iterate by name so members with
        # 0 activeness (no visible number) are still captured.
        name_blocks.sort(key=lambda b: b.box.center.y)

        pairs: list[tuple[str | None, str | None]] = []
        used_activeness_indices: set[int] = set()

        for nb in name_blocks:
            name_y = nb.box.center.y

            # Find the nearest activeness block within the search radius
            best_act: str | None = None
            best_dist = float("inf")
            best_idx = -1
            for idx, ab in enumerate(activeness_blocks):
                if idx in used_activeness_indices:
                    continue
                dist = abs(ab.box.center.y - name_y)
                if dist <= self._Y_ACTIVENESS_PAIR_RADIUS and dist < best_dist:
                    best_dist = dist
                    best_act = ab.text.strip()
                    best_idx = idx

            if best_act is not None and best_idx >= 0:
                used_activeness_indices.add(best_idx)
                pairs.append((nb.text.strip(), best_act))
            else:
                # No activeness block found for this member — weekly reset or
                # truly inactive.  Include them with activeness=0.
                pairs.append((nb.text.strip(), "0"))

        pairs_before_qwen = len(pairs)
        self._recover_orphaned_activeness_names(
            screenshot, activeness_blocks, used_activeness_indices, pairs
        )

        if self._ocr_debug is not None:
            self._ocr_debug.append(
                {
                    "type": "activeness",
                    "frame": frame_label,
                    "name_blocks": [
                        {"text": b.text, "cy": b.box.center.y} for b in name_blocks
                    ],
                    "activeness_blocks": [
                        {"text": b.text, "cy": b.box.center.y}
                        for b in activeness_blocks
                    ],
                    "pairs": list(pairs[:pairs_before_qwen]),
                    "qwen_recovered": list(pairs[pairs_before_qwen:]),
                }
            )
        return pairs

    def _recover_orphaned_activeness_names(
        self,
        screenshot,
        activeness_blocks: list,
        used_indices: set[int],
        pairs: list[tuple[str | None, str | None]],
    ) -> None:
        """Ask Qwen to name-read rows whose activeness value has no paired name.

        Handles members whose name RapidOCR cannot detect (e.g. Korean Hangul).
        Crops the name column of each orphaned row and passes it to Qwen.
        """
        qwen: QwenVLOCRBackend | None = getattr(self, "_activeness_qwen", None)
        if qwen is None:
            return
        for i, ab in enumerate(activeness_blocks):
            if i in used_indices:
                continue
            cy = ab.box.center.y
            crop = screenshot[
                max(0, cy - self._Y_ACTIVENESS_PAIR_RADIUS) : min(
                    screenshot.shape[0], cy + self._Y_ACTIVENESS_PAIR_RADIUS
                ),
                : self._X_ACTIVENESS_MIN,
            ]
            name = qwen.extract_player_name(crop)
            if name and self._is_valid_activeness_name(name):
                pairs.append((name.strip(), ab.text.strip()))

    _RE_CHEST_LABEL = re.compile(
        r"chest\s*contribution|contribution\s*ranking|guild\s*chest"
        r"|distribution|activeness\s*required"
        r"|officer|founder|paladin|knight|squire|member",
        re.IGNORECASE,
    )
    _RE_CHEST_ROLE = re.compile(
        r"^(officer|founder|paladin|knight|squire|member)$", re.IGNORECASE
    )

    def _parse_chest_contribution_rows(  # noqa: PLR0912
        self,
        screenshot,
        ocr_backend: OCRBackend,
        frame_label: str | None = None,
    ) -> list[tuple[str, int]]:
        """Return (raw_name, chest_count) pairs from one Contribution Ranking frame."""
        ocr_results = ocr_backend.detect_text_blocks(screenshot)
        area = [
            r
            for r in ocr_results
            if self._Y_CHEST_CONTRIB_MIN <= r.box.center.y <= self._Y_CHEST_CONTRIB_MAX
        ]

        # Single pass: split area into value_blocks (right) and name_blocks (left).

        # OCR may prefix the number with a chest icon char (e.g. '￥8', '个8').
        value_blocks = []
        name_blocks = []
        for b in area:
            t = b.text.strip()
            m = self._RE_CHEST_VALUE.match(t)
            if (
                b.box.center.x > self._X_CHEST_NAME_MAX
                and m is not None
                and 0 <= int(m.group(1)) <= self._MAX_CHEST_VALUE
                and not self._RE_CHEST_LABEL.search(t)
            ):
                value_blocks.append(b)
                continue
            if b.box.center.x >= self._X_CHEST_NAME_MAX:
                continue
            if not t or len(t) < self._MIN_NAME_LENGTH:
                continue
            if self._RE_CHEST_LABEL.search(t):
                continue
            # Skip pure rank numbers on the far left (x≈105); member names like
            # "67" appear at x≈350+ and must not be filtered.
            if (
                t.isdigit()
                and int(t) <= self._MAX_CHEST_RANK_NUMBER
                and b.box.center.x < self._X_CHEST_RANK_BADGE_MAX
            ):
                continue
            name_blocks.append(b)

        # Pair each name block with the nearest value block by Y distance
        name_blocks.sort(key=lambda b: b.box.center.y)
        pairs: list[tuple[str, int]] = []
        used_values: set[int] = set()
        for nb in name_blocks:
            name_y = nb.box.center.y
            best_val, best_dist, best_idx = None, float("inf"), -1
            for idx, vb in enumerate(value_blocks):
                if idx in used_values:
                    continue
                dist = abs(vb.box.center.y - name_y)
                if dist <= self._Y_CHEST_PAIR_RADIUS and dist < best_dist:
                    m = self._RE_CHEST_VALUE.match(vb.text.strip())
                    if m is not None:
                        best_dist, best_val, best_idx = dist, int(m.group(1)), idx
            if best_val is not None:
                used_values.add(best_idx)
                pairs.append((nb.text.strip(), best_val))

        pairs_before_qwen = len(pairs)
        self._supplement_pairs_with_qwen_chest(screenshot, pairs)

        if self._ocr_debug is not None:
            self._ocr_debug.append(
                {
                    "type": "chest",
                    "frame": frame_label,
                    "name_blocks": [
                        {"text": b.text, "cx": b.box.center.x, "cy": b.box.center.y}
                        for b in name_blocks
                    ],
                    "value_blocks": [
                        {"text": b.text, "cx": b.box.center.x, "cy": b.box.center.y}
                        for b in value_blocks
                    ],
                    "pairs_rapid": list(pairs[:pairs_before_qwen]),
                    "pairs_qwen": list(pairs[pairs_before_qwen:]),
                }
            )
        return pairs

    def _supplement_pairs_with_qwen_chest(
        self,
        screenshot,
        pairs: list[tuple[str, int]],
    ) -> None:
        """Add Qwen-detected chest entries not found by RapidOCR (e.g. Korean)."""
        qwen: QwenVLOCRBackend | None = getattr(self, "_activeness_qwen", None)
        if qwen is None:
            return
        qwen_pairs = qwen.extract_chest_from_screenshot(screenshot)
        if not qwen_pairs:
            return
        # Only accept Qwen names that fuzzy-match a real guild member (≥ 0.65).
        # This rejects hallucinations like "Boga" that do not match any member.
        guild_members: list[str] = getattr(self, "_guild_members", None) or []
        suffix_pat = re.compile(r"\b[A-Za-z]?\d{3,4}\b")
        cleaned_members = [
            self._clean_member_name(m, suffix_pat) for m in guild_members
        ]
        existing_lower = {n.lower() for n, _ in pairs}
        for qname, qchest in qwen_pairs:
            if not qname or len(qname) < self._MIN_NAME_LENGTH:
                continue
            if any(
                SequenceMatcher(None, qname.lower(), e).ratio()
                >= self._FUZZY_DEDUP_THRESHOLD
                for e in existing_lower
            ):
                continue
            # Reject if the name doesn't resemble any guild member.
            if guild_members:
                qname_clean = self._clean_member_name(qname, suffix_pat)
                best_ratio = max(
                    (
                        SequenceMatcher(None, qname_clean, cm).ratio()
                        for cm in cleaned_members
                    ),
                    default=0.0,
                )
                if best_ratio < self._GUILD_NAME_CORRECTION_THRESHOLD:
                    continue
            try:
                m = self._RE_CHEST_VALUE.match(qchest or "")
                chest_int = int(m.group(1)) if m else 0
            except (ValueError, AttributeError):
                chest_int = 0
            if 0 <= chest_int <= self._MAX_CHEST_VALUE:
                pairs.append((qname, chest_int))
                existing_lower.add(qname.lower())

    def _navigate_to_chest_contribution_ranking(self, nav_backend: OCRBackend) -> bool:
        """From the Guild Hall, open Guild Chest and tap Contribution Ranking tab.

        Returns True if the Contribution Ranking screen is reached.
        """
        guild_chest_btn = None
        for attempt in range(self._MAX_CHEST_NAV_RETRIES):
            screenshot = self.get_screenshot()
            ocr_results = nav_backend.detect_text_blocks(screenshot)
            guild_chest_btn = next(
                (
                    r
                    for r in ocr_results
                    if "guild" in r.text.strip().lower()
                    and "chest" in r.text.strip().lower()
                ),
                None,
            )
            if guild_chest_btn is not None:
                break
            if attempt < self._MAX_CHEST_NAV_RETRIES - 1:
                logging.info(
                    "Guild Chest button not found yet, "
                    "waiting for guild hall to load..."
                )
                sleep(3)
        if guild_chest_btn is None:
            logging.warning("Guild Chest button not found - skipping chest scan.")
            return False

        logging.info(f"Tapping Guild Chest at {guild_chest_btn.box.center}.")
        self.tap(guild_chest_btn.box.center)
        sleep(2.5)

        screenshot = self.get_screenshot()
        ocr_results = nav_backend.detect_text_blocks(screenshot)
        contrib_tab = next(
            (
                r
                for r in ocr_results
                if (
                    "contribution" in r.text.strip().lower()
                    or "ranking" in r.text.strip().lower()
                )
                and r.box.center.y >= self._Y_TAB_MIN
            ),
            None,
        )
        if contrib_tab is None:
            logging.warning("Contribution Ranking tab not found - skipping chest scan.")
            self.press_back_button()
            sleep(1.5)
            return False

        logging.info(f"Tapping Contribution Ranking tab at {contrib_tab.box.center}.")
        self.tap(contrib_tab.box.center)
        sleep(2)
        return True

    def _collect_chest_contribution_scroll(
        self, nav_backend: OCRBackend
    ) -> dict[str, int]:
        """Scroll through the Contribution Ranking and return raw name->chest dict."""
        seen_names: set[str] = set()
        contributions: dict[str, int] = {}
        no_new_count = 0

        for scroll_idx in range(self._MAX_SCROLLS_CHEST):
            screenshot = self.get_screenshot()
            self._save_debug_screenshot(screenshot, f"chest_{scroll_idx:03d}")
            pairs = self._parse_chest_contribution_rows(
                screenshot, nav_backend, frame_label=f"chest_{scroll_idx:03d}"
            )

            new_this_frame = False
            for raw_name, chest_count in pairs:
                name = re.sub(r"\s*[A-Za-z]?\d{3,4}\s*$", "", raw_name).strip()
                if not name or len(name) < self._MIN_NAME_LENGTH:
                    continue
                if self._find_fuzzy_match(name, seen_names) is None:
                    seen_names.add(name)
                    contributions[name] = chest_count
                    new_this_frame = True
                    logging.debug(f"Chest contribution: {name!r} = {chest_count}")

            no_new_count = 0 if new_this_frame else no_new_count + 1
            if no_new_count >= self._MAX_NO_NEW_CHEST:
                logging.info(
                    f"No new entries for {self._MAX_NO_NEW_CHEST} consecutive "
                    "scrolls. Finished chest contribution scan."
                )
                break

            self.swipe_up(x=540, sy=1400, ey=1100, duration=1.5)
            sleep(2.0)

        return contributions

    def _scan_guild_chest_contributions(
        self,
        nav_backend: OCRBackend,
        guild_members: list[str] | None = None,
    ) -> dict[str, int]:
        """Navigate to Guild Chest Contribution Ranking and return name->chest dict.

        Assumes the Guild Hall is already on screen. Returns empty dict on failure.
        """
        if not self._navigate_to_chest_contribution_ranking(nav_backend):
            return {}

        logging.info("Scanning Guild Chest Contribution Ranking...")
        contributions = self._collect_chest_contribution_scroll(nav_backend)

        if guild_members:
            corrected: dict[str, int] = {}
            for raw_name, count in contributions.items():
                fixed = self._correct_single_name(raw_name, guild_members)
                corrected[fixed] = max(corrected.get(fixed, 0), count)
            contributions = corrected

        logging.info(f"Collected chest contributions for {len(contributions)} members.")
        self.press_back_button()
        sleep(1.5)
        return contributions

    def _collect_activeness_scroll_data(self, ocr_backend: OCRBackend) -> list[dict]:
        """Scroll the Members list and return raw activeness records."""
        seen_names: set[str] = set()
        seen_index: dict[str, int] = {}
        records: list[dict] = []
        no_new_count = 0

        sleep(10)

        for scroll_idx in range(self._MAX_SCROLLS_ACTIVENESS):
            screenshot = self.get_screenshot()
            self._save_debug_screenshot(screenshot, f"activeness_{scroll_idx:03d}")
            pairs = self._parse_activeness_rows(
                screenshot, ocr_backend, frame_label=f"activeness_{scroll_idx:03d}"
            )

            new_this_frame = False
            for raw_name, activeness in pairs:
                if not raw_name:
                    continue
                name = re.sub(r"\s*[A-Za-z]?\d{3,4}\s*$", "", raw_name).strip()
                if not name or len(name) < self._MIN_NAME_LENGTH:
                    continue
                try:
                    activeness_int = int(activeness) if activeness is not None else 0
                except ValueError:
                    activeness_int = 0
                already_seen = self._find_fuzzy_match(name, seen_names)
                if already_seen is None:
                    seen_names.add(name)
                    seen_index[name] = len(records)
                    records.append({"Name": name, "Activeness": activeness_int})
                    new_this_frame = True
                    logging.debug(f"Guild activeness: {name!r} = {activeness_int}")
                elif activeness_int > records[seen_index[already_seen]]["Activeness"]:
                    records[seen_index[already_seen]]["Activeness"] = activeness_int
                    logging.debug(
                        f"Guild activeness: updated {already_seen!r} "
                        f"-> {activeness_int}"
                    )

            no_new_count = 0 if new_this_frame else no_new_count + 1
            if no_new_count >= self._MAX_NO_NEW_ACTIVENESS:
                logging.info(
                    f"No new members for {self._MAX_NO_NEW_ACTIVENESS} consecutive "
                    "scrolls. Finished activeness scan."
                )
                break

            self.swipe_up(x=540, sy=1400, ey=800, duration=1.0)
            sleep(2)

        return records

    def _scan_guild_activeness(
        self,
        ocr_backend: OCRBackend,
        guild_members: list[str] | None = None,
    ) -> None:
        """Navigate to the Guild Members screen and scan all member activeness."""
        # Navigation labels ("Guild", "Members") are English — always use RapidOCR.
        nav_backend = RapidOCRBackend()
        # Store Qwen backend (if available) for multilingual name supplement.
        self._activeness_qwen: QwenVLOCRBackend | None = (
            ocr_backend if isinstance(ocr_backend, QwenVLOCRBackend) else None
        )

        # Navigate to the Guild Hall first, then scan chest contributions.
        # _scan_guild_chest_contributions ends with press_back_button() back to
        # the Guild Hall; _navigate_to_guild_members_screen re-enters from there.
        chest_contributions: dict[str, int] = {}
        if self._navigate_to_guild_hall(nav_backend):
            chest_contributions = self._scan_guild_chest_contributions(
                nav_backend, guild_members
            )

        if not self._navigate_to_guild_members_screen(nav_backend):
            logging.error(
                "Could not reach Guild Members screen. Skipping activeness scan."
            )
            return

        logging.info("Scanning Guild Members activeness...")
        activeness_records = self._collect_activeness_scroll_data(ocr_backend)

        if guild_members:
            activeness_records = self._filter_and_correct_activeness_records(
                activeness_records, guild_members
            )

        if chest_contributions:
            for record in activeness_records:
                record["ChestContribution"] = chest_contributions.get(record["Name"], 0)

        logging.info(
            f"Collected activeness for {len(activeness_records)} guild members."
        )
        self._save_guild_activeness_to_json(activeness_records)

    def _filter_and_correct_activeness_records(
        self,
        records: list[dict],
        guild_members: list[str],
    ) -> list[dict]:
        """Correct names, discard non-guild noise, and deduplicate by name."""
        suffix_pat = re.compile(r"\b[A-Za-z]?\d{3,4}\b")
        cleaned_members = [
            (m, self._clean_member_name(m, suffix_pat)) for m in guild_members
        ]
        corrected: list[dict] = []
        for entry in records:
            best_match, best_ratio = self._find_best_member_match(
                entry["Name"], cleaned_members, suffix_pat
            )
            if best_ratio >= self._GUILD_NAME_CORRECTION_THRESHOLD:
                entry["Name"] = best_match
                corrected.append(entry)
            else:
                logging.warning(
                    f"Activeness: discarding non-guild name {entry['Name']!r} "
                    f"(best ratio {best_ratio:.2f})"
                )
        # Keep the highest activeness value when the same member appears twice
        dedup: dict[str, dict] = {}
        for entry in corrected:
            key = entry["Name"]
            if key not in dedup or entry["Activeness"] > dedup[key]["Activeness"]:
                dedup[key] = entry
        return list(dedup.values())

    def _correct_single_name(self, name: str, guild_members: list[str]) -> str:
        """Return the closest guild member name to `name`."""
        suffix_pat = re.compile(r"\b[A-Za-z]?\d{3,4}\b")
        cleaned_members = [
            (m, self._clean_member_name(m, suffix_pat)) for m in guild_members
        ]
        best_match, best_ratio = self._find_best_member_match(
            name, cleaned_members, suffix_pat
        )
        return (
            best_match if best_ratio >= self._GUILD_NAME_CORRECTION_THRESHOLD else name
        )

    def _save_guild_activeness_to_json(self, records: list[dict]) -> None:
        """Save guild activeness records to guild_activeness.json."""
        if not records:
            logging.warning("No guild activeness data collected.")
            return
        try:
            data_root = SettingsLoader.get_app_config_dir()
            output_dir = data_root / "data"
            os.makedirs(output_dir, exist_ok=True)
            output_file = output_dir / "guild_activeness.json"
            with open(output_file, mode="w", encoding="utf-8") as f:
                json.dump(records, f, indent=4, ensure_ascii=False)
            logging.info(
                f"Successfully exported {len(records)} guild activeness entries."
            )
            logging.info(f"Output file path: {output_file}")
        except Exception as e:
            logging.error(f"Failed to save guild activeness JSON: {e}")

    def _scan_supreme_arena(  # noqa: PLR0915
        self,
        ocr_backend: OCRBackend,
        fallback: OCRBackend | None = None,
        guild_members: list[str] | None = None,
    ) -> None:
        """Scan Supreme Arena rankings, filter by Guild Members, and export results."""
        logging.info("Entering Supreme Arena...")
        self.navigate_to_battle_modes_screen()
        try:
            mode = self._find_in_battle_modes(
                "battle_modes/supreme_arena.png",
                "Failed to find Supreme Arena.",
            )
            self.tap(mode)
            self.sleep_navigation()
        except GameTimeoutError as fail:
            logging.error(f"{fail} {self.LANG_ERROR}")
            raise

        # Tap Rankings button in Supreme Arena
        logging.info("Tapping Rankings button in Supreme Arena...")
        # Supreme Arena rankings button matches the standard rankings cup icon
        # or similar. Let's use OCR or look for standard cup.
        # Standard rankings template for arena is 'arena/dr_ranking.png'
        # or 'dream_realm/dr_ranking.png'.
        # Let's search using the 'dream_realm/dr_ranking.png' template.
        try:
            reward = self.wait_for_template(
                "supreme_arena/rankings.png",
                timeout_message=("Could not find Rankings button in Supreme Arena."),
                timeout=self.min_timeout,
            )
            self.tap(reward)
            sleep(2)
        except GameTimeoutError:
            # Fallback to dream_realm template
            try:
                reward = self.wait_for_template(
                    "dream_realm/dr_ranking.png",
                    timeout_message=(
                        "Could not find Rankings button in Supreme Arena."
                    ),
                    timeout=self.min_timeout,
                )
                self.tap(reward)
                sleep(2)
            except GameTimeoutError:
                # Fallback to OCR if template fails
                logging.warning(
                    "Could not find rankings button template, trying OCR..."
                )
            screenshot = self.get_screenshot()
            ocr_results = ocr_backend.detect_text_blocks(screenshot)
            found = False
            for res in ocr_results:
                text = res.text.lower()
                # Check for rankings specifically on the right sidebar (x > 800)
                if (
                    "rank" in text or "classif" in text
                ) and res.box.center.x > self._X_SIDEBAR_BOUNDARY:
                    logging.info(
                        f"Found Rankings button via OCR at {res.box.center}, tapping."
                    )
                    self.tap(res.box.center)
                    found = True
                    sleep(2)
                    break
            if not found:
                raise AutoPlayerWarningError(
                    "Failed to find Rankings button in Supreme Arena."
                )

        # Set filter to Guild Members
        if not self._set_guild_members_filter(ocr_backend):
            logging.warning(
                "Could not set filter to Guild Members. "
                "Rankings may contain all players."
            )

        # Check for scroll-to-top button and click it if present
        scroll_top_btn = self.game_find_template_match(
            "dream_realm/scroll_top.png",
            threshold=ConfidenceValue("80%"),
        )
        if scroll_top_btn:
            logging.info("Found scroll-to-top button, tapping to reset list to top.")
            self.tap(scroll_top_btn.box.center)
            sleep(2)

        # Scroll and scan the rankings
        day_name = datetime.datetime.now().strftime("%A")  # e.g., "Monday"
        logging.info(f"Scanning Supreme Arena rankings for {day_name}...")

        # Supreme Arena does not have date tabs, so we scan directly
        sa_rankings = self._scan_rankings_for_current_date(
            day_name, ocr_backend, fallback, is_supreme_arena=True
        )
        sa_rankings = self._correct_names_with_guild_members(
            sa_rankings, guild_members or []
        )

        # Save Supreme Arena rankings to JSON
        if sa_rankings:
            try:
                data_root = SettingsLoader.get_app_config_dir()
                output_dir = data_root / "data"
                os.makedirs(output_dir, exist_ok=True)
                output_file = output_dir / "supreme_arena_rankings.json"

                with open(output_file, mode="w", encoding="utf-8") as f:
                    json.dump(sa_rankings, f, indent=4, ensure_ascii=False)

                logging.info(
                    f"Successfully exported {len(sa_rankings)} "
                    "Supreme Arena ranking entries."
                )
                logging.info(f"Output file path: {output_file}")
            except Exception as e:
                logging.error(f"Failed to save Supreme Arena rankings JSON: {e}")
        else:
            logging.warning("No Supreme Arena rankings data collected.")

    def _save_debug_screenshot(self, screenshot, name: str) -> None:
        if self._screenshot_dir is None:
            return
        try:
            path = self._screenshot_dir / f"{name}.png"
            cv2.imwrite(str(path), screenshot)
        except Exception as e:
            logging.warning(f"Could not save debug screenshot {name}: {e}")

    def _save_ocr_debug(self) -> None:
        """Write raw OCR frames to ocr_debug.json for troubleshooting."""
        if self._ocr_debug is None:
            return
        try:
            data_root = SettingsLoader.get_app_config_dir()
            output_dir = data_root / "data"
            os.makedirs(output_dir, exist_ok=True)
            output_file = output_dir / "ocr_debug.json"
            payload = {
                "api_url": self.settings.guild_manager_scan.guild_members_api_url,
                "frames": self._ocr_debug,
            }
            with open(output_file, mode="w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            logging.info(f"OCR debug data written to {output_file}")
        except Exception as e:
            logging.warning(f"Could not write OCR debug file: {e}")
