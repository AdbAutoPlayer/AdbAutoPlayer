"""Guild scan: setup, constants, OCR backend selection, debug utilities."""

import importlib.util
import logging
import re
import shutil
import site
import subprocess
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
from adb_auto_player.exceptions import AutoPlayerWarningError
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.ocr import OCRBackend, RapidOCRBackend
from adb_auto_player.ocr.qwen2vl_backend import QwenVLOCRBackend

if TYPE_CHECKING:
    from typing import Any

    from adb_auto_player.games.afk_journey.settings import Settings

    class BaseClass:
        settings: Settings
        LANG_ERROR: str
        min_timeout: float
        fast_timeout: float
        device: Any
        template_timeout: float
        _ocr_debug: list[dict] | None
        _screenshot_dir: Any

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


class _GuildScanSetupMixin(BaseClass):
    """Constants, OCR backend selection, package management, debug output."""

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
    _Y_GUILD_NAV_MIN = 1840
    _Y_GUILD_NAV_MAX = 1920
    _GUILD_SWIPE_SX = 700
    _GUILD_SWIPE_SY = 600
    _GUILD_SWIPE_EX = 300
    _GUILD_SWIPE_EY = 1200
    _Y_ACTIVENESS_MIN = 320
    _Y_ACTIVENESS_MAX = 1800
    _X_ACTIVENESS_MIN = 500
    _Y_ACTIVENESS_ROW_TOLERANCE = 60
    _Y_ACTIVENESS_PAIR_RADIUS = 120
    _MIN_ACTIVENESS_VALUE = 10
    _MAX_ACTIVENESS_VALUE = 9999
    _MAX_NO_NEW_ACTIVENESS = 5
    _GUILD_NAV_SWIPE_MAX_ATTEMPTS = 2
    _GUILD_NAME_CORRECTION_THRESHOLD = 0.65

    # Guild Chest contribution ranking scan constants
    _Y_CHEST_CONTRIB_MIN = 850
    _Y_CHEST_CONTRIB_MAX = 1800
    _X_CHEST_NAME_MAX = 480
    _Y_CHEST_PAIR_RADIUS = 150
    _MAX_CHEST_VALUE = 200
    _MAX_SCROLLS_CHEST = 44
    _MAX_NO_NEW_CHEST = 5
    _MAX_CHEST_NAV_RETRIES = 3
    _MAX_CHEST_RANK_NUMBER = 200
    _X_CHEST_RANK_BADGE_MAX = 200
    _RE_CHEST_VALUE = re.compile(r"^\D{0,3}(\d+)$")

    def __init__(self) -> None:
        """Initialize _GuildScanSetupMixin."""
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
        extras = _GuildScanSetupMixin._extras_dir()
        if not extras.exists():
            return
        extras_str = str(extras)
        if extras_str not in sys.path:
            sys.path.append(extras_str)
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
        extras_dir = _GuildScanSetupMixin._extras_dir()
        extras_dir.mkdir(parents=True, exist_ok=True)

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
            _GuildScanSetupMixin._activate_extras()
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
        for dist_info in _GuildScanSetupMixin._extras_dir().glob("torch-*.dist-info"):
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
        has_cuda, _ = _GuildScanSetupMixin._torch_metadata()
        return has_cuda

    def _ensure_qwen2vl_packages(self, confirmed: bool) -> None:
        """Install or fix torch+Qwen2-VL deps, ensuring GPU (CUDA) support."""
        torch_present = importlib.util.find_spec("torch") is not None
        torchvision_present = importlib.util.find_spec("torchvision") is not None
        transformers_present = importlib.util.find_spec("transformers") is not None
        tiktoken_present = importlib.util.find_spec("tiktoken") is not None

        has_cuda, torch_ver = self._torch_metadata()
        need_torch = (
            not torch_present
            or not torchvision_present
            or not has_cuda
            or torch_ver < (2, 7)
        )
        need_others = not transformers_present or not tiktoken_present

        if not need_torch and not need_others:
            return

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

        cuda_index = "https://download.pytorch.org/whl/cu126"

        if need_torch:
            action = "Reinstalling" if torch_present else "Installing"
            logging.info(f"{action} PyTorch with CUDA 12.6 support...")
            if not self._pip_install(
                ["torch", "torchvision"],
                index_url=cuda_index,
                no_deps=True,
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
        import json  # noqa: PLC0415
        import os  # noqa: PLC0415

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
