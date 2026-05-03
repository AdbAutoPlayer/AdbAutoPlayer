from __future__ import annotations

import json
import logging
import os
import re
import shutil
import time
import urllib.request
from difflib import SequenceMatcher, get_close_matches
from pathlib import Path

import cv2
import numpy as np

# Removed circular import with AFKJourneyBase
from adb_auto_player.decorators.register_command import register_command
from adb_auto_player.file_loader.settings_loader import SettingsLoader
from adb_auto_player.games.afk_journey.gui_category import AFKJCategory
from adb_auto_player.models.decorators import GUIMetadata
from adb_auto_player.models.geometry import Point
from rapidocr import RapidOCR

logger = logging.getLogger(__name__)

WHALE_THRESHOLD = 25
PARAGON_LOCK_THRESHOLD = 15


# OCR Synonyms are now loaded from data/hero_synonyms.json


ASCENSION_OCR_MAP = {
    # Paragon ranks (Vertical badges often read as C', C", etc.)
    "C '": "Paragon 1",
    "C'": "Paragon 1",
    "C  ": "Paragon 1",
    "Paragon äºº": "Paragon 1",
    "Paragon 1": "Paragon 1",
    "Paragon 2": "Paragon 2",
    "Paragon 3": "Paragon 3",
    "Paragon 4": "Paragon 4",
    "Crown": "Paragon 4",
    "Crowns": "Paragon 4",
    # Specific misreads
    # Common Misreads
    "Subreme": "Supreme",
    "Suprem": "Supreme",
    "Lvthic": "Mythic",
    "Mvthic": "Mythic",
    "Legend": "Legendary",
    # Garbage tokens found in Full Roster scans for Epic heroes
    "ï¿¥": "Epic",
}

# Ascension ranks that do NOT have EX weapons unlocked
BELOW_MYTHIC_PLUS = [
    "Not Owned",
    "Epic",
    "Epic+",
    "Legendary",
    "Legendary+",
    "Mythic",
    "Elite+",
    "Elite",
    "Unknown",
]

# Coordinates for Improved Ascension OCR (Ascend Panel)
COORD_BTN_ASCEND = (350, 1830)
COORD_BTN_BACK_PANEL = (100, 1830)
# Region for "Current Â» Future" text in the Ascend panel: (x, y, w, h)
# Expanded to 550px height to cover all vertical drift positions (Y=800 to Y=1350)
REGION_ASCEND_LINE = (50, 800, 980, 550)


class HeroScannerMixin:
    """Mixin for AFK Journey Hero Scanning.

    This mixin provides methods for automated roster scanning.
    Expects to be mixed into a class that provides Game and Navigation methods.
    """

    def _get_project_root(self) -> Path:
        """Determines the project root directory.

        Handles both development (source) and production (installed) environments.
        """
        try:
            resource_dir = SettingsLoader.get_resource_dir()
            # In Dev mode, resource_dir is typically nested inside
            # src-tauri/src-python/adb_auto_player
            if "src-python" in resource_dir.parts:
                # Find the index of 'src-python'
                try:
                    p_idx = resource_dir.parts.index("src-python")
                    # If the parent is 'src-tauri', go one level higher to
                    # find the true project root
                    if p_idx > 0 and resource_dir.parts[p_idx - 1] == "src-tauri":
                        return Path(*resource_dir.parts[: p_idx - 1])
                    return Path(*resource_dir.parts[:p_idx])
                except (ValueError, IndexError):
                    pass

            # In Production mode, resource_dir is the installation root
            # or Resources folder (macOS)
            return resource_dir
        except Exception:
            # Fallback for standalone scripts if SettingsLoader isn't fully initialized
            # Relative to this file: games/afk_journey/mixins/hero_scanner.py
            # 6 levels up should hit the root in source.
            return Path(__file__).parents[6]

    def _load_synonyms(self):
        """Loads synonyms from data/hero_synonyms.json.

        Prefers the downloaded version in the app config directory.
        """
        self.hero_synonyms = {}

        # 1. Check User Data (Downloaded version)
        data_root = SettingsLoader.get_app_config_dir()
        user_synonym_path = data_root / "data" / "hero_synonyms.json"

        # 2. Check Project Root (Bundled version)
        project_root = self._get_project_root()
        bundled_synonym_path = project_root / "data" / "hero_synonyms.json"

        # Prioritize the user-downloaded file
        paths_to_check = [user_synonym_path, bundled_synonym_path]

        for synonym_path in paths_to_check:
            if synonym_path.exists():
                try:
                    with open(synonym_path, encoding="utf-8") as f:
                        self.hero_synonyms = json.load(f)
                    logger.debug(
                        f"Loaded {len(self.hero_synonyms)} hero name synonyms"
                        f" from {synonym_path}."
                    )
                    return  # Found and loaded, stop searching
                except Exception as e:
                    logger.error(f"Failed to load synonyms from {synonym_path}: {e}")

        logger.warning("No synonym files found.")

    def _ocr_text_rapid(self, image: np.ndarray, crop: tuple | None = None) -> str:
        """Helper to get text using RapidOCR.

        Args:
            image: The image to process.
            crop: Optional crop coordinates.

        Returns:
            The extracted text.
        """
        if not hasattr(self, "rapid_ocr"):
            # Constructor no longer takes det_db parameters in this version
            self.rapid_ocr = RapidOCR()

        # Use default parameters for inference to avoid TypeError in this version.
        # 3x Upscaling (done outside or provided in image) is the key for '+' detection.
        result = self.rapid_ocr(image)
        if result:
            # New RapidOCROutput format (v1.3.0+)
            if hasattr(result, "txts") and result.txts:
                return " ".join(result.txts).strip()  # ty: ignore[no-matching-overload]

            # Handle list/tuple format
            texts = []
            results_list = result if isinstance(result, list) else [result]
            for line in results_list:
                if isinstance(line, (list, tuple)) and len(line) > 1:
                    texts.append(str(line[1]))
                elif isinstance(line, str):
                    texts.append(line)
            return " ".join(texts).strip()
        return ""

    @register_command(
        name="HeroScanner",
        gui=GUIMetadata(
            label="AFKJ Tracker Scan",
            category=AFKJCategory.EVENTS_AND_OTHER,
            tooltip="Scan your hero roster for the AFKJ Tracker website",
        ),
    )
    def scan_roster(self, total_heroes: int | None = None):  # noqa: PLR0912, PLR0915
        """Scans the entire hero roster and updates the backup tracker.

        Args:
            total_heroes: Optional limit on the number of heroes to scan.
                If None, the scan continues until Hammie or Chippy is found.
        """
        if total_heroes is None:
            # We determine the limit by hero count in settings if possible
            try:
                total_heroes = (
                    len(self.settings.general.excluded_heroes) + 100  # ty: ignore[unresolved-attribute]
                )
            except Exception:
                total_heroes = 120

        limit: int = total_heroes

        template_url = f"https://afkj-tracker.vercel.app/data/heroes-template.json?v={int(time.perf_counter())}"
        synonyms_url = f"https://afkj-tracker.vercel.app/data/hero_synonyms.json?v={int(time.perf_counter())}"

        # User Data (Writable)
        data_root = SettingsLoader.get_app_config_dir()
        template_file = data_root / "data" / "heroes-template.json"
        synonyms_file = data_root / "data" / "hero_synonyms.json"
        backup_file = data_root / "data" / "afkj_tracker_backup.json"

        # 1A. Download Synonyms
        try:
            logger.info(f"Downloading synonyms from: {synonyms_url}")
            os.makedirs(synonyms_file.parent, exist_ok=True)
            with (
                urllib.request.urlopen(synonyms_url) as response,
                open(synonyms_file, "wb") as out_file,
            ):
                shutil.copyfileobj(response, out_file)
            logger.info(f"Synonyms downloaded to {synonyms_file}")
            # Force reload of synonyms after download
            self._load_synonyms()
        except Exception as e:
            logger.error(f"Failed to download synonyms: {e}")
            # Fallback happens in _load_synonyms automatically

        # 1B. Download Template
        try:
            logger.info(f"Downloading template from: {template_url}")
            os.makedirs(template_file.parent, exist_ok=True)
            with (
                urllib.request.urlopen(template_url) as response,
                open(template_file, "wb") as out_file,
            ):
                shutil.copyfileobj(response, out_file)
            logger.info(f"Template downloaded to {template_file}")
        except Exception as e:
            logger.error(f"Failed to download template: {e}")
            if not template_file.exists():
                logger.error(
                    "Template file missing and download failed. Aborting scan."
                )
                return

        # 2. Setup Persistence
        self.tracker_file = str(template_file)

        # 3. Navigation to Hall
        self.navigate_to_resonating_hall()  # ty: ignore[unresolved-attribute]
        self.sleep_navigation()  # ty: ignore[unresolved-attribute]

        # 4. Load Data
        full_data = self._load_tracker(self.tracker_file)
        if not full_data or "heroes" not in full_data:
            logger.error(
                f"Could not load heroes list from template file: {self.tracker_file}"
            )
            return

        # Build dynamic list of hero names for OCR matching
        self.canonical_hero_names = [h["name"] for h in full_data.get("heroes", [])]
        logger.info(
            f"Loaded {len(self.canonical_hero_names)} hero names from template."
        )

        heroes_scanned = 0
        global_ascend_available = False
        paragons_unlocked_confirmed = False

        # Navigate to the first hero once (Antandra or Top-Left)
        first_hero_point = Point(130, 1050)
        self.tap(first_hero_point)  # ty: ignore[unresolved-attribute]
        self.sleep_navigation()  # ty: ignore[unresolved-attribute]

        while heroes_scanned < limit:  # Safety cap, stop on Hammie/Chippy
            try:
                screenshot = self.get_screenshot()  # ty: ignore[unresolved-attribute]
                hero_data = self._process_hero_screen(screenshot)

                # 2. Check for Terminator Heroes (Hammie/Chippy) - Stop condition
                if hero_data["name"] in ["Hammie", "Chippy"]:
                    logger.info(
                        f"Target hero {hero_data['name']} found. Stopping scan."
                    )
                    break

                # 3. Update JSON
                if hero_data["name"] != "Unknown":
                    # Logic Fix: Detect if the hero is maxed or needs deep scan
                    button_status = self._ascend_button_is_present()

                    if button_status is True:
                        global_ascend_available = True
                        logger.debug(
                            f"Ascend button found for {hero_data['name']}"
                            " - Triggering Deep Scan"
                        )
                        deep_asc = self._scan_ascension_from_panel(
                            hero_data["name"], hero_data["ascension"]
                        )
                        if deep_asc != "Unknown":
                            hero_data["ascension"] = deep_asc

                        # Live Update: If we found a Paragon 1-3, we confirm Paragons
                        if any(
                            p in hero_data["ascension"]
                            for p in ["Paragon 1", "Paragon 2", "Paragon 3"]
                        ):
                            paragons_unlocked_confirmed = True
                    # Logic: Missing 'Ascend' button means CAPPED (S+ or P4)
                    # Use Live Tracking to disambiguate immediately
                    elif paragons_unlocked_confirmed:
                        hero_data["ascension"] = "Paragon 4"
                        logger.debug(
                            f"Missing buttons for {hero_data['name']} "
                            "(Paragons Unlocked) -> Forced Paragon 4"
                        )
                    else:
                        hero_data["ascension"] = "Pending S+/P4"
                        logger.debug(
                            f"Missing buttons for {hero_data['name']} "
                            "-> Forced Pending S+/P4"
                        )

                    # RE-PARSE EX WEAPON now that we have the corrected rank
                    hero_data["ex_weapon"] = self._parse_ex_level(
                        hero_data["raw_ex"], hero_data["ascension"], hero_data["name"]
                    )

                    hero_data["currentAscension"] = hero_data["ascension"]
                    hero_data["currentExWeaponLevel"] = hero_data["ex_weapon"]
                    self._update_hero_in_json(full_data, hero_data)

                    logger.info(
                        f"Scan Hero #{heroes_scanned + 1}: {hero_data['name']} | "
                        f"{hero_data['ascension']} | EX {hero_data['ex_weapon']}"
                    )
                else:
                    logger.warning("!!! IDENTIFICATION FAILED !!! ")
                    logger.warning(
                        f"Hero #{heroes_scanned + 1} - Raw OCR: "
                        f"'{hero_data['raw_name']}'"
                    )

                heroes_scanned += 1

                # 5. Navigate Next
                next_arrow = Point(1045, 1080)
                self.tap(next_arrow)  # ty: ignore[unresolved-attribute]
                self.sleep_navigation()  # ty: ignore[unresolved-attribute]
            except Exception as e:
                logger.error(f"Error during scan at hero #{heroes_scanned + 1}: {e}")
                # Try to recover by skipping to next hero
                next_arrow = Point(1045, 1080)
                self.tap(next_arrow)  # ty: ignore[unresolved-attribute]
                self.sleep_navigation()  # ty: ignore[unresolved-attribute]
                heroes_scanned += 1

        # Go back to main hall
        self.press_back_button()  # ty: ignore[unresolved-attribute]

        # Post-process any heroes that were locked out of the Ascend panel
        self.resolve_locked_paragons(full_data, global_ascend_available)

        # Rename template to backup
        try:
            if template_file.exists():
                logger.info(f"Renaming {template_file} to {backup_file}...")
                if backup_file.exists():
                    os.remove(backup_file)
                shutil.move(str(template_file), str(backup_file))
                logger.info("Scan results finalized in backup file.")
        except Exception as e:
            logger.error(f"Failed to rename scan result to backup: {e}")

        logger.info(f"Diagnostic scan completed! {heroes_scanned} processed.")
        logger.info(
            "SCAN COMPLETED: You can now import the results into "
            "https://afkj-tracker.vercel.app/ using the file at this path:"
        )
        logger.info(
            f">>> {backup_file} <<<",
            extra={"no_sanitize": True},
        )

    def resolve_locked_paragons(
        self, full_data: dict, global_ascend_available: bool = False
    ):
        """Resolves any heroes marked as 'Paragon Locked' or 'Pending S+/P4'.

        Uses roster unlock thresholds and global button availability to
        determine the actual rank.

        Args:
            full_data: The full tracker JSON data to be updated.
            global_ascend_available: Whether any 'Ascend' button was seen.
        """
        heroes = full_data.get("heroes", [])

        # 1. Determine if Paragons are unlocked and possible
        # (need >= 25 Supreme+ equivalents)
        sup_and_p_count = sum(
            1
            for h in heroes
            if h.get("currentAscension")
            in [
                "Supreme+",
                "Paragon 1",
                "Paragon 2",
                "Paragon 3",
                "Paragon 4",
                "Pending S+/P4",
                "Paragon Locked",
            ]
        )

        has_p123 = any(
            h.get("currentAscension") in ["Paragon 1", "Paragon 2", "Paragon 3"]
            for h in heroes
        )

        paragon_possible = sup_and_p_count >= WHALE_THRESHOLD

        # Paragon is only truly unlocked if they have met the threshold AND
        # either have > P1 heroes or NO buttons across the entire account
        # (mega whale).
        is_paragon_unlocked = paragon_possible and (
            has_p123 or not global_ascend_available
        )

        # 2. Resolve 'Pending' cases based on global context (Retroactive fix)
        self._resolve_pending_heroes(
            heroes, is_paragon_unlocked, global_ascend_available
        )

        # 3. Safety Check: If Paragon is locked/impossible.
        # This securely catches F2P accounts with >25 S+ where the server
        # hasn't unlocked Paragons yet, and downgrades their 'no need' heroes.
        if not is_paragon_unlocked:
            self._downgrade_misread_paragons(heroes)

        # 4. Handle 'Paragon Locked' (the tooltip case)
        self._resolve_locked_heroes(heroes)

        # Save final state to file
        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=4, ensure_ascii=False)

    def _resolve_pending_heroes(
        self, heroes: list, is_paragon_unlocked: bool, global_ascend_available: bool
    ):
        """Resolves 'Pending S+/P4' heroes."""
        pending_heroes = [
            h for h in heroes if h.get("currentAscension") == "Pending S+/P4"
        ]
        if not pending_heroes:
            return

        # NEW LOGIC: If Paragons are unlocked (seen P1/2/3 OR mega whale),
        # then heroes without buttons ARE Paragon 4 as S+ would show 'Ascend'.
        if is_paragon_unlocked:
            resolved_pending = "Paragon 4"
            logger.info(
                f"Resolving {len(pending_heroes)} 'Pending S+/P4' heroes to "
                "'Paragon 4' (Paragons Unlocked on account)."
            )
        else:
            resolved_pending = "Supreme+"
            logger.info(
                f"Resolving {len(pending_heroes)} 'Pending S+/P4' heroes to "
                "'Supreme+' (Paragons likely locked)."
            )

        for h in pending_heroes:
            h["currentAscension"] = resolved_pending

    def _downgrade_misread_paragons(self, heroes: list):
        """Downgrades misidentified Paragon ranks to Supreme+."""
        misread_paragons = [
            h
            for h in heroes
            if h.get("currentAscension") is not None
            and "Paragon" in h.get("currentAscension", "")
            and h.get("currentAscension") != "Paragon Locked"
        ]
        if misread_paragons:
            logger.info(
                f"Paragon tier locked (< {WHALE_THRESHOLD} S+). Downgrading "
                f"{len(misread_paragons)} misidentified Paragon ranks "
                "to 'Supreme+'."
            )
            for h in misread_paragons:
                h["currentAscension"] = "Supreme+"

    def _resolve_locked_heroes(self, heroes: list):
        """Resolves 'Paragon Locked' heroes based on roster counts."""
        p1_list = ["Paragon 1", "Paragon 2", "Paragon 3", "Paragon 4", "Paragon Locked"]
        p2_list = ["Paragon 2", "Paragon 3", "Paragon 4", "Paragon Locked"]
        sup_list = ["Supreme+", *p1_list]

        sup_count = sum(1 for h in heroes if h.get("currentAscension") in sup_list)
        p1_count = sum(1 for h in heroes if h.get("currentAscension") in p1_list)
        p2_count = sum(1 for h in heroes if h.get("currentAscension") in p2_list)

        # Count-based fallback for 'Paragon Locked' only
        if sup_count < WHALE_THRESHOLD:
            resolved_locked = "Supreme+"
        elif p1_count < PARAGON_LOCK_THRESHOLD:
            resolved_locked = "Paragon 1"
        elif p2_count < PARAGON_LOCK_THRESHOLD:
            resolved_locked = "Paragon 2"
        else:
            resolved_locked = "Paragon 3"

        locked_heroes = [
            h for h in heroes if h.get("currentAscension") == "Paragon Locked"
        ]
        if locked_heroes:
            logger.info(
                f"Resolving {len(locked_heroes)} 'Paragon Locked' heroes"
                f" to '{resolved_locked}' "
                f"(Counts - S+: {sup_count}, P1: {p1_count}, P2: {p2_count})"
            )
            for h in locked_heroes:
                h["currentAscension"] = resolved_locked

    def _update_hero_in_json(self, full_data: dict, hero_data: dict):
        """Finds hero by name in the 'heroes' list and updates fields.

        Args:
            full_data: The full tracker JSON data.
            hero_data: The dictionary containing updated hero information.
        """
        target_name = hero_data["name"]
        for hero in full_data["heroes"]:
            if hero["name"].lower() == target_name.lower():
                hero["currentAscension"] = hero_data["ascension"]
                hero["currentExWeaponLevel"] = hero_data["ex_weapon"]
                hero["last_scanned"] = time.perf_counter()
                break

        # Atomic-ish save
        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=4)

    def _load_tracker(self, file_path: str) -> dict:
        """Loads the tracker JSON data from a file.

        Args:
            file_path: Absolute path to the tracker JSON file.

        Returns:
            The loaded JSON data as a dictionary, or an empty dict if it fails.
        """
        if os.path.exists(file_path):
            try:
                with open(file_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading tracker: {e}")
        return {}

    def _ascend_button_is_present(self) -> bool | str:
        """Checks if 'Ascend', 'Level Cap', or 'Phase' is present at the bottom.

        Returns:
            True if Ascend found, 'MAXED' if Level Cap found,
            'LEVELING' if Level Up found.
        """
        # Expanded region to better capture 'Level Up' buttons and multiple lines
        region_btn_check = (100, 1740, 700, 160)
        x1, y1, w, h = region_btn_check
        full_ss = self.get_screenshot()  # ty: ignore[unresolved-attribute]
        btn_img = full_ss[y1 : y1 + h, x1 : x1 + w]
        btn_img_scaled = cv2.resize(
            btn_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
        )
        btn_text = self._ocr_text_rapid(btn_img_scaled, None).lower().strip()

        if not btn_text:
            logger.debug("Button area check: empty OCR text")
            return False

        # 1. PRIORITY: Check for 'ascend' or 'supplement' FIRST.
        active_keywords = ["ascend", "supplement"]
        if any(kw in btn_text for kw in active_keywords):
            logger.debug(f"Button area check: '{btn_text}' -> ascend/supplement found")
            return True

        for word in btn_text.split():
            if any(
                SequenceMatcher(None, word, kw).ratio() >= 0.75  # noqa: PLR2004
                for kw in active_keywords
            ):
                logger.debug(
                    f"Button area check: '{btn_text}' -> '{word}' found (fuzzy)"
                )
                return True

        logger.debug(f"Button area check: '{btn_text}' -> nothing found")
        return False

    def _scan_ascension_from_panel(  # noqa: PLR0912, PLR0915
        self, hero_name: str, initial_rank: str = "Unknown"
    ) -> str:
        """Opens the Ascension Panel and uses OCR to confirm the current rank.

        Args:
            hero_name: The name of the hero (for logging/debug).
            initial_rank: The rank detected from the vertical badge (initial guess).

        Returns:
            The detected ascension rank string or 'Paragon Locked'.
        """
        # 1. Click the Ascend button
        self.tap(Point(COORD_BTN_ASCEND[0], COORD_BTN_ASCEND[1]))  # ty: ignore[unresolved-attribute]
        self.sleep_action()  # ty: ignore[unresolved-attribute]

        full_ss = self.get_screenshot()  # ty: ignore[unresolved-attribute]

        # 2. Check if a tooltip popped up instead of the full panel
        # When a hero's ascension is locked by Resonance (e.g., Lily May),
        # clicking the padlocked Ascend button shows a tooltip.
        tooltip_crop = full_ss[1300:1700, 50:1030]
        tooltip_text = self._ocr_text_rapid(tooltip_crop, None).lower()
        if "requirements" in tooltip_text or "unlock" in tooltip_text:
            logger.debug("Detected Ascend lock tooltip!")
            # 1. Tap portrait to dismiss tooltip (enters zoom mode)
            self.tap(Point(540, 400))  # ty: ignore[unresolved-attribute]
            self.sleep_action()  # ty: ignore[unresolved-attribute]
            # 2. Tap back to exit zoom mode and return to hero screen
            self.tap(Point(COORD_BTN_BACK_PANEL[0], COORD_BTN_BACK_PANEL[1]))  # ty: ignore[unresolved-attribute]
            self.sleep_action()  # ty: ignore[unresolved-attribute]
            # Return our special temporary placeholder
            return "Paragon Locked"

        # 3. Capture and OCR the full ascension line (Current Â» Future)
        x1, y1, w, h = REGION_ASCEND_LINE
        panel_crop = full_ss[y1 : y1 + h, x1 : x1 + w]

        # Upscale the crop to help OCR read the small font sizes
        scaled_crop = cv2.resize(
            panel_crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
        )
        full_line_text = self._ocr_text_rapid(scaled_crop, None)

        # 4. OCR Rivalry/Basic Stats for Paragon disambiguation
        # The stats box is below the ascension line, safely covering Y=1050 to Y=1750
        stats_crop = full_ss[1050:1750, 50:1030]
        # Upscale the stats to ensure numbers like 14 or 15 are read perfectly
        scaled_stats = cv2.resize(
            stats_crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
        )

        stats_text = self._ocr_text_rapid(scaled_stats, None).upper()

        # 5. Determine if we are in Rivalry (Paragon) stats or Basic stats

        # 6. Close the panel (Back button)
        self.tap(Point(COORD_BTN_BACK_PANEL[0], COORD_BTN_BACK_PANEL[1]))  # ty: ignore[unresolved-attribute]
        self.sleep_action()  # ty: ignore[unresolved-attribute]

        # 6. Parse the "Current Â» Future" logic (Main detection)
        if not full_line_text:
            return "Unknown"

        # ... (rest of _normalize_panel_text remains)
        def _normalize_panel_text(t: str) -> str:
            """Normalizes text for the ascension panel OCR.

            Args:
                t: The raw OCR text.

            Returns:
                Normalized text.
            """
            t = re.sub(r"(Paragon)(\d)", r"\1 \2", t, flags=re.IGNORECASE)
            t = t.strip()
            return t

        full_line_text = _normalize_panel_text(full_line_text)

        # 6. Sequential Header Scan (First rank is current, second is target)
        all_header_matches = []
        possible_bases = ["Supreme", "Mythic", "Legendary", "Elite", "Epic"]

        # 1. Exact/Synonym matches from map
        for pattern, canonical in ASCENSION_OCR_MAP.items():
            for m in re.finditer(re.escape(pattern.lower()), full_line_text.lower()):
                all_header_matches.append((m.start(), canonical))

        # 2. Fuzzy base matches
        for base in possible_bases:
            for m in re.finditer(re.escape(base.lower()), full_line_text.lower()):
                idx = m.start()
                # Check for plus-suffix in the header
                search_area = full_line_text[idx + len(base) : idx + len(base) + 2]
                plus_chars = ["+", "å  "]
                if base.lower() in ["supreme", "mythic"]:
                    plus_chars.extend(["t", "k", "*", "f", "v", "i", "l", "1"])
                is_plus = any(c in search_area for c in plus_chars)
                rank_name = f"{base}+" if is_plus and not base.endswith("+") else base
                all_header_matches.append((idx, rank_name))

        # 3. Conflict Resolution: For each unique position, keep only the BEST match
        pos_map = {}  # idx -> rank_name
        for idx, rank_name in all_header_matches:
            if idx not in pos_map:
                pos_map[idx] = rank_name
            else:
                existing = pos_map[idx]
                if len(rank_name) > len(existing) or (
                    "+" in rank_name and "+" not in existing
                ):
                    pos_map[idx] = rank_name

        # Convert back to sorted list
        found_header_ranks = sorted(pos_map.items(), key=lambda x: x[0])

        current_rank = initial_rank  # Start with the side-badge guess
        current_rank_idx = -1
        future_rank = "Unknown"

        if found_header_ranks:
            logger.debug(f"Header Scan for {hero_name} found: {found_header_ranks}")

            # CONSENSUS LOGIC: Try to find rank that confirms our guess.
            # This prevents stray noise (like 'TltdraT') from being picked.
            match_found = False
            for i, (idx, rank) in enumerate(found_header_ranks):
                if rank.lower() == initial_rank.lower():
                    current_rank = rank
                    current_rank_idx = i
                    match_found = True
                    logger.debug(
                        f"Consensus reached for {hero_name}: {rank} matches side-badge."
                    )
                    break

            # Fallback: If no consensus, take the first one (left-to-right)
            if not match_found:
                current_rank = found_header_ranks[0][1]
                current_rank_idx = 0
                logger.debug(
                    f"No consensus for {hero_name}: fallback to {current_rank}."
                )

            # Identify the future rank (the one to the right of current)
            if len(found_header_ranks) > current_rank_idx + 1:
                future_rank = found_header_ranks[current_rank_idx + 1][1]

        # 6. Future-Rank Deduction (Deduce current rank from the upcoming goal)
        if future_rank != "Unknown":
            # Case A: Future is Paragon X -> Current is Supreme+ or Paragon X-1
            if "paragon" in future_rank.lower():
                if "paragon" in current_rank.lower():
                    numbers = [int(s) for s in future_rank.split() if s.isdigit()]
                    if numbers:
                        p_lvl = numbers[0] - 1
                        if p_lvl > 0:
                            current_rank = f"Paragon {p_lvl}"
                elif "supreme" in current_rank.lower() or current_rank == "Unknown":
                    current_rank = "Supreme+"
                    logger.debug(
                        f"Future Deduction for {hero_name}: {future_rank} Goal"
                        " -> Current Supreme+"
                    )

        # 7. Statistics Fallback & Keyword Correction
        # To avoid over-correction (like L -> L+), we ONLY run this if the
        # header scan was Unknown or for high-tier ranks where misreads
        # are common.
        do_fallback = current_rank == "Unknown" or any(
            kw in current_rank.lower() for kw in ["supreme", "mythic", "paragon"]
        )

        combined_context = (full_line_text + " " + stats_text).upper()
        if do_fallback:
            rank_patterns = [
                (r"PARAGON (\d)", lambda m: f"Paragon {m.group(1)}"),
                (r"SUPREME[\s]*[\+t\*kåvfi1l|]", "Supreme+"),
                (r"SUPREME", "Supreme"),
                (r"MYTHIC[\s]*[\+t\*kåvfi1l|]", "Mythic+"),
                (r"MYTHIC", "Mythic"),
                (r"LEGENDARY[\s]*[\+t\*kåvfi1l|]", "Legendary+"),
                (r"LEGENDARY", "Legendary"),
                (r"EPIC[\s]*[\+t\*kåvfi1l|]", "Epic+"),
                (r"EPIC", "Epic"),
            ]

            found_ranks = []
            for pattern, rank_val in rank_patterns:
                # Use search on the combined context to find the earliest/clearest match
                match = re.search(pattern, combined_context, re.IGNORECASE)
                if match:
                    found_ranks.append(
                        (
                            match.start(),
                            (callable(rank_val) and rank_val(match)) or rank_val,  # ty: ignore[call-top-callable]
                        )
                    )

            if found_ranks:
                # Sort by start position ASCENDING to find the current rank
                found_ranks.sort(key=lambda x: (x[0], -len(x[1])))

                # Only override if the found rank is more precise
                # (has a plus or is paragon) OR if current detection was Unknown.
                if (
                    current_rank == "Unknown"
                    or "paragon" in found_ranks[0][1].lower()
                    or ("+" in found_ranks[0][1] and "+" not in current_rank)
                ):
                    logger.debug(
                        f"Fallback Correction for {hero_name}: "
                        f"{current_rank} -> {found_ranks[0][1]}"
                    )
                    current_rank = found_ranks[0][1]

        # 8. Unified Numeric Milestone Logic - ABSOLUTE FINAL PRIORITY
        # This is the "Gold Standard": if we see a milestone, it defines rank.

        # KEY PROTECTION: Milestones are only valid in "Rivalry Stats" (S+).
        # Basic Stats (ATK, HP) are full of noise (15%, 25,000).
        has_rivalry = "RIVALRY" in stats_text.upper()

        if has_rivalry:
            # Clean text: ignore skills (which have noise like "25 Life Drain")
            clean_stats = stats_text
            for stop_word in [
                "Skill Unlocked",
                "Enhance Force",
                "Skill Description",
                "Unlocked at",
            ]:
                idx = clean_stats.lower().find(stop_word.lower())
                if idx != -1:
                    clean_stats = clean_stats[:idx]
                    break

            # IMPROVED REGEX: Ignore numbers followed by '%'
            all_milestones_regex = r"(?<!\d)(0|1|2|3|14|15|25|30|37|45|48|60)(?!\d|%)"
            nums = re.findall(all_milestones_regex, clean_stats)

            if nums:
                num_ints = [int(n) for n in nums]
                target_goal = max(num_ints)
                master_goal_map = {
                    14: "Supreme",
                    25: "Supreme+",
                    37: "Paragon 1",
                    48: "Paragon 2",
                    15: "Supreme+",
                    30: "Paragon 1",
                    45: "Paragon 2",
                    60: "Paragon 3",
                }
                if target_goal in master_goal_map:
                    # This is the gold standard. We trust numbers above all else.
                    current_rank = master_goal_map[target_goal]
                    logger.debug(
                        f"Gold Standard for {hero_name}: Milestone "
                        f"{target_goal} -> {current_rank}"
                    )
        else:
            logger.debug(f"Rivalry Shield for {hero_name}: skipping numeric milestones")

        logger.debug(
            f"Deep Scan for {hero_name}: '{full_line_text}' -> Final: {current_rank}"
        )
        return current_rank

    def _get_precise_name_crop(self, screenshot: np.ndarray) -> np.ndarray:
        """Dynamically detect the text block for the hero name.

        Avoids titles and orbs. Verified coordinates for 1080p:
        Avoids titles like 'Wasteland Apothecary' and 'Corpsemaker'.
        """
        # 1. Targeted ROI (centered on the expected name area)
        # Narrowed Y to frame the name: Expanded to 60-200 to ensure no cutting
        roi_y_start, roi_y_end = 60, 200
        roi_x_start, roi_x_end = 110, 950
        wide_crop = screenshot[roi_y_start:roi_y_end, roi_x_start:roi_x_end]

        # 2. Pre-process to find shapes (grayscale + OTSU threshold)
        gray = cv2.cvtColor(wide_crop, cv2.COLOR_BGR2GRAY)
        # Use OTSU to dynamically find the best threshold for text vs background
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 3. Find contours (shapes)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        candidates = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # Filter for hero letters: lower height (40) to be inclusive
            if h > 40 and w > 10:  # noqa: PLR2004
                candidates.append((x, y, x + w, y + h))

        if not candidates:
            # Fallback: Return the whole ROI if no clear text is found
            return wide_crop

        # Calculate bounding box of all candidates
        min_x = min(c[0] for c in candidates)
        min_y = min(c[1] for c in candidates)
        max_x = max(c[2] for c in candidates)
        max_y = max(c[3] for c in candidates)

        # 4. Add padding and crop (increased to 20 for more context)
        pad = 20
        p_x = max(0, min_x - pad)
        p_y = max(0, min_y - pad)
        p_w = min(wide_crop.shape[1] - p_x, (max_x - min_x) + pad * 2)
        p_h = min(wide_crop.shape[0] - p_y, (max_y - min_y) + pad * 2)

        precise_name_img = wide_crop[p_y : p_y + p_h, p_x : p_x + p_w]
        return precise_name_img

    def _process_hero_screen(self, screenshot: np.ndarray) -> dict:
        """Extract name, ascension and EX level from hero screen."""
        # 1. OCR Regions (1080p)
        crop_asc = (5, 5, 130, 170)  # Vertical badge
        crop_ex = (
            10,
            1400,
            450,
            1650,
        )  # Inclusive crop for weapon and resonance context

        # 2. Process Name (Super-Vision Triple-OCR Strategy)
        name_img = self._get_precise_name_crop(screenshot)
        name_img_scaled = cv2.resize(
            name_img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
        )
        gray_name = cv2.cvtColor(name_img_scaled, cv2.COLOR_BGR2GRAY)

        # Strategy A: Standard Grayscale
        raw_name_a = self._ocr_text_rapid(gray_name, None)

        # Strategy B: OTSU Threshold (Hard Contrast)
        _, thresh_name = cv2.threshold(
            gray_name, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        raw_name_b = self._ocr_text_rapid(thresh_name, None)

        # Strategy C: Sharpness-boosted (for thin letters)
        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened_name = cv2.filter2D(gray_name, -1, kernel)
        raw_name_c = self._ocr_text_rapid(sharpened_name, None)

        # Combine all perspectives for a super-robust match
        raw_names = [raw_name_a, raw_name_b, raw_name_c]
        name = self._match_hero_name(raw_names)

        if name == "Unknown":
            logger.debug(
                f"Super-Vision identification failed. Combined Raw: {raw_names}"
            )

        asc_img = screenshot[crop_asc[1] : crop_asc[3], crop_asc[0] : crop_asc[2]]
        asc_img_scaled = cv2.resize(
            asc_img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
        )
        raw_asc = self._ocr_text_rapid(asc_img_scaled, None)

        # 3. Process EX Level (Robust Multi-Preprocessing)
        ex_img = screenshot[crop_ex[1] : crop_ex[3], crop_ex[0] : crop_ex[2]]
        ex_img_scaled = cv2.resize(
            ex_img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
        )
        gray_ex = cv2.cvtColor(ex_img_scaled, cv2.COLOR_BGR2GRAY)

        # Strategy A: OTSU Inverted (Standard for light text on dark)
        _, thresh_a = cv2.threshold(
            gray_ex, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        raw_ex_a = self._ocr_text_rapid(thresh_a, None)

        # Strategy B: OTSU Normal (For dark text on light)
        _, thresh_b = cv2.threshold(
            gray_ex, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        raw_ex_b = self._ocr_text_rapid(thresh_b, None)

        # Combine results for parsing
        raw_ex_combined = f"{raw_ex_a} {raw_ex_b}"

        ascension = self._match_ascension(raw_asc)
        ex = self._parse_ex_level(raw_ex_combined, ascension, name)

        # Combine for dictionary output
        raw_name = " ".join(raw_names)

        return {
            "name": name,
            "raw_name": raw_name,
            "raw_asc": raw_asc,
            "ascension": ascension,
            "ex_weapon": ex,
            "raw_ex": raw_ex_combined,
        }

    def _prepare_hero_matching_data(
        self, raw_input: str | list[str]
    ) -> tuple[list[str], str, list[dict], list[str]]:
        """Prepares metadata and tokens required for hero matching.

        Returns:
            A tuple of (readings, raw_text, hero_meta, all_ocr_tokens).
        """
        if isinstance(raw_input, list):
            readings = [r for r in raw_input if r.strip()]
            raw_text = " ".join(readings)
        else:
            readings = [raw_input]
            raw_text = raw_input

        # Prepare hero metadata from roster
        hero_meta = []
        if hasattr(self, "canonical_hero_names"):
            for h in self.canonical_hero_names:
                norm = re.sub(r"[^a-zA-Z0-9]", "", h).lower().replace("and", "")
                h_tokens = [
                    re.sub(r"[^a-zA-Z0-9]", "", t).lower()
                    for t in h.split()
                    if len(t) > 2  # noqa: PLR2004
                ]
                hero_meta.append({"name": h, "norm": norm, "tokens": h_tokens})

        # Extract OCR tokens from all readings
        all_ocr_tokens = []
        for r in readings:
            all_ocr_tokens.extend(
                [
                    re.sub(r"[^a-zA-Z0-9]", "", t).lower()
                    for t in r.split()
                    if len(t) >= 2  # noqa: PLR2004
                ]
            )

        return readings, raw_text, hero_meta, all_ocr_tokens

    def _match_independent_strategies(
        self, readings: list[str], hero_meta: list[dict], all_ocr_tokens: list[str]
    ) -> str | None:
        """Executes token-intersection and independent reading strategies."""
        # 1.1: Token Intersection (Covers fragments split by noise)
        for h in hero_meta:
            if not h["tokens"]:
                continue
            matches_count = 0
            for h_token in h["tokens"]:
                if any(h_token in ocr_t for ocr_t in all_ocr_tokens):
                    matches_count += 1
            if matches_count == len(h["tokens"]):
                logger.debug(f"MATCH STRATEGY: [TOKEN-INTERSECT] -> '{h['name']}'")
                return h["name"]

        # 1.2: Reading-Level Substring (Clean hit in one strategy)
        for reading in readings:
            reading_clean = re.sub(r"[^a-zA-Z0-9]", "", reading).lower()
            for h in hero_meta:
                if len(h["norm"]) >= 4 and h["norm"] in reading_clean:  # noqa: PLR2004
                    logger.debug(
                        f"MATCH STRATEGY: [INDEPENDENT-SUB] "
                        f"'{reading}' -> '{h['name']}'"
                    )
                    return h["name"]

        # 1.3: Token-to-Hero Fragment
        for ocr_t in all_ocr_tokens:
            if len(ocr_t) < 5:  # noqa: PLR2004
                continue
            for h in hero_meta:
                if ocr_t in h["norm"]:
                    logger.debug(
                        f"MATCH STRATEGY: [TOKEN-FRAGMENT] '{ocr_t}' -> '{h['name']}'"
                    )
                    return h["name"]
        return None

    def _match_synonym_strategies(
        self, raw_text: str, text_clean: str, all_ocr_tokens: list[str]
    ) -> str | None:
        """Executes synonym-based matching strategies."""
        if not hasattr(self, "hero_synonyms"):
            self._load_synonyms()

        synonym_matches = []
        # Pass 3.1: Token-Based
        for token in all_ocr_tokens:
            for pattern_raw, canonical in self.hero_synonyms.items():
                pattern = re.sub(r"[^a-zA-Z0-9]", "", pattern_raw).lower()
                if not pattern:
                    continue
                if (len(pattern) < 5 and token == pattern) or (  # noqa: PLR2004
                    len(pattern) >= 5 and pattern in token  # noqa: PLR2004
                ):
                    synonym_matches.append((len(pattern), canonical))

        # Pass 3.2: Joined-Context
        for pattern_raw, canonical in self.hero_synonyms.items():
            pattern = re.sub(r"[^a-zA-Z0-9]", "", pattern_raw).lower()
            if len(pattern) >= 4 and pattern in text_clean:  # noqa: PLR2004
                synonym_matches.append((len(pattern), canonical))

        if synonym_matches:
            synonym_matches.sort(key=lambda x: x[0], reverse=True)
            best_name = synonym_matches[0][1]
            logger.debug(f"MATCH STRATEGY: [SYNONYM-BEST] '{best_name}'")
            return best_name
        return None

    def _match_fuzzy_fallback_strategies(self, text_clean: str) -> str | None:
        """Executes long substring and fuzzy matching strategies."""
        norm_to_canonical = {
            re.sub(r"[^a-zA-Z0-9]", "", name).lower(): name
            for name in self.canonical_hero_names
        }

        # 4. Long substring match fallback
        if len(text_clean) >= 6:  # noqa: PLR2004
            for norm, canonical in norm_to_canonical.items():
                if text_clean in norm or norm in text_clean:
                    logger.debug(f"MATCH STRATEGY: [SUBSTRING] -> '{canonical}'")
                    return canonical

        # 5. Final Fallback: Fuzzy matching (Very Strict)
        possible_norms = list(norm_to_canonical.keys())
        matches = get_close_matches(text_clean, possible_norms, n=1, cutoff=0.85)
        if matches:
            canonical = norm_to_canonical[matches[0]]
            norm_match = matches[0]
            if len(norm_match) < 6:  # noqa: PLR2004
                if not get_close_matches(text_clean, [norm_match], n=1, cutoff=0.95):
                    return None
            logger.debug(f"MATCH STRATEGY: [FUZZY] -> '{canonical}'")
            return canonical
        return None

    def _match_hero_name(self, raw_input: str | list[str]) -> str:
        """Matches raw OCR input to a canonical hero name using multiple strategies."""
        if not raw_input:
            return "Unknown"

        readings, raw_text, hero_meta, all_ocr_tokens = (
            self._prepare_hero_matching_data(raw_input)
        )
        text_clean = re.sub(r"[^a-zA-Z0-9]", "", raw_text).lower()
        if not text_clean:
            return "Unknown"

        # 1. Independent Reading Search (STRONGEST STRATEGY)
        match = self._match_independent_strategies(readings, hero_meta, all_ocr_tokens)
        if not match:
            # 2. Exact Match Fallback (Joined string)
            norm_to_canonical = {
                re.sub(r"[^a-zA-Z0-9]", "", name).lower(): name
                for name in self.canonical_hero_names
            }
            if text_clean in norm_to_canonical and len(text_clean) >= 3:  # noqa: PLR2004
                logger.debug(
                    f"MATCH STRATEGY: [EXACT] -> '{norm_to_canonical[text_clean]}'"
                )
                match = norm_to_canonical[text_clean]

        if not match:
            # 3. Synonyms Match
            match = self._match_synonym_strategies(raw_text, text_clean, all_ocr_tokens)

        if not match:
            # 4 & 5. Fallback & Fuzzy
            match = self._match_fuzzy_fallback_strategies(text_clean)

        return match or "Unknown"

    def _match_ascension(self, raw_text: str) -> str:
        """Determines the ascension rank from raw OCR text.

        Args:
            raw_text: The OCR text from the badge or panel.

        Returns:
            The canonical ascension rank string.
        """
        if not raw_text:
            return "Unknown"
        text = raw_text.strip()

        # 1. Direct pattern match - we take match that appears EARLIEST.
        # This is critical for lines where 'Paragon' might appear as a goal.
        best_match = None
        earliest_index = 999

        for pattern, canonical in ASCENSION_OCR_MAP.items():
            idx = text.lower().find(pattern.lower())
            if idx != -1 and idx < earliest_index:
                earliest_index = idx
                best_match = canonical

        if best_match:
            return best_match

        # 2. Lowercase for fuzzy
        text = text.lower()

        # 3. Base ranks fuzzy matching
        possible_bases = ["Supreme", "Mythic", "Legendary", "Elite", "Epic"]

        # Check for multiple base ranks and pick the earliest
        found_matches = []
        for base in possible_bases:
            idx = text.find(base.lower())
            if idx != -1:
                found_matches.append((idx, base))

        if found_matches:
            # Sort by position (index)
            found_matches.sort(key=lambda x: x[0])
            base_rank = found_matches[0][1]

            # Tightened search area for "+" to avoid matching next word
            search_start = text.lower().find(base_rank.lower()) + len(base_rank)
            # We only look 2 characters ahead now for greater precision
            search_area = text[max(0, search_start) : search_start + 2]

            # Check for '+' or common OCR noise that looks like a '+'
            # Elite/Epic/Legendary have huge '+' signs that don't get misread as text.
            plus_chars = ["+", "å  "]
            # 'i', 'l', '1', 't', 'k', 'f', 'v', '*' are common border artifacts.
            # We only accept them as '+' for high ranks where '+' is tiny.
            if base_rank.lower() in ["supreme", "mythic"]:
                plus_chars.extend(["t", "k", "*", "f", "v", "i", "l", "1"])

            is_plus = any(c in search_area for c in plus_chars)

            if is_plus and not base_rank.endswith("+"):
                return f"{base_rank}+"
            return base_rank

        return "Unknown"

    def _parse_ex_level(
        self, raw_text: str, current_ascension: str, hero_name: str = "Unknown"
    ) -> int:
        """Parses the EX weapon level with robust noise handling.

        Args:
            raw_text: The OCR text from the weapon area.
            current_ascension: The verified ascension rank.
            hero_name: The name of the hero (for debugging).

        Returns:
            The parsed EX weapon level (0-40).
        """
        # 1. Eligibility Check: EX Weapons strictly unlock at Mythic+
        eligible_ranks = [
            "Mythic+",
            "Supreme",
            "Supreme+",
            "Pending S+/P4",
            "Paragon Locked",
            "Paragon 1",
            "Paragon 2",
            "Paragon 3",
            "Paragon 4",
        ]
        if not any(r in current_ascension for r in eligible_ranks):
            return 0

        # 2. Clean seasonal & UI lock noise labels first
        cleaned = raw_text.upper()
        # Remove "LVL. 9", "RESONANCE 240", or "REACH SUPREME+" (UI Noise)
        cleaned = re.sub(r"LVL\.?\s*\d+", " ", cleaned)
        cleaned = re.sub(r"RESONANCE\.?\s*\d+", " ", cleaned)
        cleaned = re.sub(r"RES\.?\s*\d+", " ", cleaned)
        cleaned = re.sub(r"REA\.?\s*\d+", " ", cleaned)
        cleaned = re.sub(r"REACH\.?\s*", " ", cleaned)

        noise_list = [
            "LEVEL",
            "LVL",
            "LV",
            "RANK",
            "EXP",
            "MAX",
            "EXCLUSIVE",
            "WEAPON",
            "RES",
            "RESONANCE",
            "REA",
            "RE ",
            "REACH",
            "UNLOCK",
            "ENHANCE",
            "FORCE",
        ]
        for noise in noise_list:
            cleaned = cleaned.replace(noise, " ")

        # 2. Prefer numbers following a '+' if possible (Highest Signal)
        # We also handle 'T', 'K', 'V' as common misreads for '+'
        text_for_plus = (
            cleaned.replace("T", "+")
            .replace("K", "+")
            .replace("V", "+")
            .replace("f", "+")
        )
        plus_matches = re.findall(r"\+\s*([0-9]{1,2})", text_for_plus)
        if plus_matches:
            valid_vals = [
                int(m)
                for m in plus_matches
                if 0 <= int(m) <= 40  # noqa: PLR2004
            ]
            if valid_vals:
                return max(valid_vals)

        # 3. Fallback for lone numbers: ONLY if no UI lock keywords were present
        if any(
            kw in raw_text.upper()
            for kw in ["LVL", "RES", "RESONANCE", "REA", "REACH", "UNLOCK"]
        ):
            # If the raw text said e.g. "Reach...", and we didn't find a "+X",
            # then any numbers found are 100% false positive noise.
            return 0

        # Look for lone numbers (not parts of other words)
        lone_nums = re.findall(r"(?<![A-Z0-9])(\d{1,2})(?![A-Z0-9])", cleaned)
        if lone_nums:
            valid_vals = [
                int(m)
                for m in lone_nums
                if 0 <= int(m) <= 40  # noqa: PLR2004
            ]
            if valid_vals:
                return max(valid_vals)

        return 0
