"""Hero scanner service for AFK Journey.

Encapsulates all roster-scanning, OCR and hero-identification logic.
The service receives a game reference on construction and delegates all device
interactions through it, keeping concerns separated from the mixin layer.
"""

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
from typing import TYPE_CHECKING

import cv2
import numpy as np
from adb_auto_player.file_loader.settings_loader import SettingsLoader
from adb_auto_player.models.geometry import Point
from rapidocr import RapidOCR

if TYPE_CHECKING:
    from adb_auto_player.games.afk_journey.base import AFKJourneyBase

logger = logging.getLogger(__name__)

# (qualifying ascensions, heroes needed, tier unlocked)
_PARAGON_THRESHOLDS: list[tuple[list[str], int, str]] = [
    (["Supreme+", "Paragon 1", "Paragon 2", "Paragon 3", "Paragon 4"], 25, "Paragon 1"),
    (["Paragon 1", "Paragon 2", "Paragon 3", "Paragon 4"], 20, "Paragon 2"),
    (["Paragon 2", "Paragon 3", "Paragon 4"], 15, "Paragon 3"),
    (["Paragon 3", "Paragon 4"], 15, "Paragon 4"),
]

_UNCERTAIN_ASCENSIONS = {"Pending S+/P4", "Paragon Locked"}

ASCENSION_OCR_MAP = {
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
    "Subreme": "Supreme",
    "Suprem": "Supreme",
    "Lvthic": "Mythic",
    "Mvthic": "Mythic",
    "Legend": "Legendary",
    "ï¿¥": "Epic",
}

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

COORD_BTN_ASCEND = (350, 1830)
COORD_BTN_BACK_PANEL = (100, 1830)
REGION_ASCEND_LINE = (50, 800, 980, 550)


class HeroScanner:
    """Encapsulates all hero-scanning logic for AFK Journey.

    Receives a reference to the running game instance and delegates all device
    interactions (screenshot, tap, navigation) through it.
    """

    def __init__(self, game: AFKJourneyBase) -> None:
        """Initialise the scanner with a game reference.

        Args:
            game: The active AFKJourneyBase instance (provides device access).
        """
        self._game = game
        self._rapid_ocr: RapidOCR | None = None
        self.hero_synonyms: dict = {}
        self.canonical_hero_names: list[str] = []
        self.tracker_file: str = ""

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def scan_roster(self, total_heroes: int | None = None) -> None:  # noqa: PLR0912, PLR0915
        """Scan the entire hero roster and write results to the backup tracker.

        Args:
            total_heroes: Optional scan limit. If None, inferred from settings.
        """
        if total_heroes is None:
            try:
                total_heroes = len(self._game.settings.general.excluded_heroes) + 200
            except Exception:
                total_heroes = 200

        limit: int = total_heroes

        template_url = (
            f"https://afkj-tracker.vercel.app/data/heroes-template.json"
            f"?v={int(time.perf_counter())}"
        )
        synonyms_url = (
            f"https://afkj-tracker.vercel.app/data/hero_synonyms.json"
            f"?v={int(time.perf_counter())}"
        )

        data_root = SettingsLoader.get_app_config_dir()
        template_file = data_root / "data" / "heroes-template.json"
        synonyms_file = data_root / "data" / "hero_synonyms.json"
        backup_file = data_root / "data" / "afkj_tracker_backup.json"

        # 1A. Download synonyms
        try:
            logger.info(f"Downloading synonyms from: {synonyms_url}")
            os.makedirs(synonyms_file.parent, exist_ok=True)
            with (
                urllib.request.urlopen(synonyms_url) as response,
                open(synonyms_file, "wb") as out_file,
            ):
                shutil.copyfileobj(response, out_file)
            logger.info(f"Synonyms downloaded to {synonyms_file}")
            self._load_synonyms()
        except Exception as e:
            logger.error(f"Failed to download synonyms: {e}")

        # 1B. Download template
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

        self.tracker_file = str(template_file)

        # 3. Navigate to hall
        self._game.navigate_to_resonating_hall()
        self._game.sleep_navigation()

        # 4. Load data
        full_data = self._load_tracker(self.tracker_file)
        if not full_data or "heroes" not in full_data:
            logger.error(
                f"Could not load heroes list from template file: {self.tracker_file}"
            )
            return

        self.canonical_hero_names = [h["name"] for h in full_data.get("heroes", [])]
        logger.info(
            f"Loaded {len(self.canonical_hero_names)} hero names from template."
        )

        if total_heroes is None:
            limit = len(self.canonical_hero_names) + 100
            logger.info(f"Adaptive scan limit set to {limit} heroes.")

        heroes_scanned = 0
        global_ascend_available = False
        paragons_unlocked_confirmed = False

        first_hero_point = Point(130, 1050)
        self._game.tap(first_hero_point)
        self._game.sleep_navigation()
        time.sleep(2)

        while heroes_scanned < limit:
            try:
                screenshot = self._game.get_screenshot()
                hero_data = self._process_hero_screen(screenshot)

                if hero_data["name"] in ["Hammie", "Chippy"]:
                    logger.info(
                        f"Target hero {hero_data['name']} found. Stopping scan."
                    )
                    break

                if hero_data["name"] != "Unknown":
                    button_status = self._ascend_button_is_present()

                    if button_status is True:
                        global_ascend_available = True
                        logger.debug(
                            f"Ascend button found for {hero_data['name']} "
                            "- Triggering Deep Scan"
                        )
                        deep_asc = self._scan_ascension_from_panel(
                            hero_data["name"], hero_data["ascension"]
                        )
                        if deep_asc != "Unknown":
                            hero_data["ascension"] = deep_asc

                        if any(
                            p in hero_data["ascension"]
                            for p in ["Paragon 1", "Paragon 2", "Paragon 3"]
                        ):
                            paragons_unlocked_confirmed = True
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
                        f"Hero #{heroes_scanned + 1}"
                        f" - Raw OCR: '{hero_data['raw_name']}'"
                    )

                heroes_scanned += 1

                next_arrow = Point(1045, 1080)
                self._game.tap(next_arrow)
                self._game.sleep_navigation()
            except Exception as e:
                logger.error(f"Error during scan at hero #{heroes_scanned + 1}: {e}")
                next_arrow = Point(1045, 1080)
                self._game.tap(next_arrow)
                self._game.sleep_navigation()
                heroes_scanned += 1

        self._game.press_back_button()
        self.resolve_locked_paragons(full_data, global_ascend_available)

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
        logger.info(f">>> {backup_file} <<<", extra={"no_sanitize": True})

    # ------------------------------------------------------------------
    # Post-scan resolution helpers
    # ------------------------------------------------------------------

    def resolve_locked_paragons(
        self, full_data: dict, global_ascend_available: bool = False
    ) -> None:
        """Resolve heroes marked as 'Paragon Locked' or 'Pending S+/P4'.

        Args:
            full_data: Full tracker JSON data to update in-place.
            global_ascend_available: Whether any 'Ascend' button was seen.
        """
        heroes = full_data.get("heroes", [])

        # Include uncertain heroes in the potential-S+ count to avoid undercounting
        # when many S+ heroes couldn't be confirmed individually during the scan.
        potential_sup_count = sum(
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

        _sup_threshold = _PARAGON_THRESHOLDS[0][1]
        paragon_globally_possible = potential_sup_count >= _sup_threshold and (
            has_p123 or not global_ascend_available
        )

        confirmed = [
            h for h in heroes if h.get("currentAscension") not in _UNCERTAIN_ASCENSIONS
        ]
        resolved_tier = self._compute_locked_tier(confirmed)

        self._resolve_pending_heroes(heroes, resolved_tier)

        if not paragon_globally_possible:
            self._downgrade_misread_paragons(heroes)

        self._resolve_locked_heroes(heroes, resolved_tier)

        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=4, ensure_ascii=False)

    def _compute_locked_tier(self, confirmed_heroes: list) -> str:
        """Determine the ascension tier for unresolved heroes from confirmed counts.

        Walks the unlock chain (S+→P1→P2→P3→P4) and returns the highest tier
        whose requirement is met by the confirmed hero counts.

        Args:
            confirmed_heroes: Heroes whose ascension is already known (not uncertain).

        Returns:
            The ascension string all uncertain heroes should receive.
        """
        resolved = "Supreme+"
        for qualifying, threshold, tier in _PARAGON_THRESHOLDS:
            count = sum(
                1 for h in confirmed_heroes if h.get("currentAscension") in qualifying
            )
            if count >= threshold:
                resolved = tier
            else:
                break
        return resolved

    def _resolve_pending_heroes(self, heroes: list, resolved_tier: str) -> None:
        pending_heroes = [
            h for h in heroes if h.get("currentAscension") == "Pending S+/P4"
        ]
        if not pending_heroes:
            return

        logger.info(
            f"Resolving {len(pending_heroes)} 'Pending S+/P4' heroes to "
            f"'{resolved_tier}'."
        )
        for h in pending_heroes:
            h["currentAscension"] = resolved_tier

    def _downgrade_misread_paragons(self, heroes: list) -> None:
        misread_paragons = [
            h
            for h in heroes
            if h.get("currentAscension") is not None
            and "Paragon" in h.get("currentAscension", "")
            and h.get("currentAscension") != "Paragon Locked"
        ]
        if misread_paragons:
            logger.info(
                f"Paragon tier locked (< 25 S+). Downgrading "
                f"{len(misread_paragons)} misidentified Paragon ranks to 'Supreme+'."
            )
            for h in misread_paragons:
                h["currentAscension"] = "Supreme+"

    def _resolve_locked_heroes(self, heroes: list, resolved_tier: str) -> None:
        # Paragon Locked heroes definitively have an Ascend button — P1 minimum.
        locked_tier = resolved_tier if "Paragon" in resolved_tier else "Paragon 1"

        locked_heroes = [
            h for h in heroes if h.get("currentAscension") == "Paragon Locked"
        ]
        if locked_heroes:
            logger.info(
                f"Resolving {len(locked_heroes)} 'Paragon Locked' heroes"
                f" to '{locked_tier}'"
            )
            for h in locked_heroes:
                h["currentAscension"] = locked_tier

    # ------------------------------------------------------------------
    # JSON persistence helpers
    # ------------------------------------------------------------------

    def _update_hero_in_json(self, full_data: dict, hero_data: dict) -> None:
        target_name = hero_data["name"]
        for hero in full_data["heroes"]:
            if hero["name"].lower() == target_name.lower():
                hero["currentAscension"] = hero_data["ascension"]
                hero["currentExWeaponLevel"] = hero_data["ex_weapon"]
                hero["last_scanned"] = time.perf_counter()
                break

        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(full_data, f, indent=4)

    def _load_tracker(self, file_path: str) -> dict:
        if os.path.exists(file_path):
            try:
                with open(file_path, encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading tracker: {e}")
        return {}

    # ------------------------------------------------------------------
    # Device interaction helpers
    # ------------------------------------------------------------------

    def _ascend_button_is_present(self) -> bool | str:
        """Check if 'Ascend', 'Level Cap', or 'Phase' is at the bottom of the screen.

        Returns:
            True if Ascend found, False otherwise.
        """
        region_btn_check = (100, 1740, 700, 160)
        x1, y1, w, h = region_btn_check
        full_ss = self._game.get_screenshot()
        btn_img = full_ss[y1 : y1 + h, x1 : x1 + w]
        btn_img_scaled = cv2.resize(
            btn_img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
        )
        btn_text = self._ocr_text_rapid(btn_img_scaled).lower().strip()

        if not btn_text:
            logger.debug("Button area check: empty OCR text")
            return False

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
        """Open the Ascension Panel and use OCR to confirm the hero's current rank.

        Args:
            hero_name: Hero name for logging.
            initial_rank: Initial rank detected from the vertical badge.

        Returns:
            The detected ascension rank string or 'Paragon Locked'.
        """
        self._game.tap(Point(COORD_BTN_ASCEND[0], COORD_BTN_ASCEND[1]))
        self._game.sleep_action()

        full_ss = self._game.get_screenshot()

        tooltip_crop = full_ss[1300:1700, 50:1030]
        tooltip_text = self._ocr_text_rapid(tooltip_crop).lower()
        if "requirements" in tooltip_text or "unlock" in tooltip_text:
            logger.debug("Detected Ascend lock tooltip!")
            self._game.tap(Point(540, 400))
            self._game.sleep_action()
            self._game.tap(Point(COORD_BTN_BACK_PANEL[0], COORD_BTN_BACK_PANEL[1]))
            self._game.sleep_action()
            return "Paragon Locked"

        x1, y1, w, h = REGION_ASCEND_LINE
        panel_crop = full_ss[y1 : y1 + h, x1 : x1 + w]
        scaled_crop = cv2.resize(
            panel_crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
        )
        full_line_text = self._ocr_text_rapid(scaled_crop)

        stats_crop = full_ss[1050:1750, 50:1030]
        scaled_stats = cv2.resize(
            stats_crop, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC
        )
        stats_text = self._ocr_text_rapid(scaled_stats).upper()

        self._game.tap(Point(COORD_BTN_BACK_PANEL[0], COORD_BTN_BACK_PANEL[1]))
        self._game.sleep_action()

        if not full_line_text:
            return "Unknown"

        def _normalize_panel_text(t: str) -> str:
            t = re.sub(r"(Paragon)(\d)", r"\1 \2", t, flags=re.IGNORECASE)
            return t.strip()

        full_line_text = _normalize_panel_text(full_line_text)

        all_header_matches = []
        possible_bases = ["Supreme", "Mythic", "Legendary", "Elite", "Epic"]

        for pattern, canonical in ASCENSION_OCR_MAP.items():
            for m in re.finditer(re.escape(pattern.lower()), full_line_text.lower()):
                all_header_matches.append((m.start(), canonical))

        for base in possible_bases:
            for m in re.finditer(re.escape(base.lower()), full_line_text.lower()):
                idx = m.start()
                search_area = full_line_text[idx + len(base) : idx + len(base) + 2]
                plus_chars = ["+", "å  "]
                if base.lower() in ["supreme", "mythic"]:
                    plus_chars.extend(["t", "k", "*", "f", "v", "i", "l", "1"])
                is_plus = any(c in search_area for c in plus_chars)
                rank_name = f"{base}+" if is_plus and not base.endswith("+") else base
                all_header_matches.append((idx, rank_name))

        pos_map: dict[int, str] = {}
        for idx, rank_name in all_header_matches:
            if idx not in pos_map:
                pos_map[idx] = rank_name
            else:
                existing = pos_map[idx]
                if len(rank_name) > len(existing) or (
                    "+" in rank_name and "+" not in existing
                ):
                    pos_map[idx] = rank_name

        found_header_ranks = sorted(pos_map.items(), key=lambda x: x[0])

        current_rank = initial_rank
        current_rank_idx = -1
        future_rank = "Unknown"

        if found_header_ranks:
            logger.debug(f"Header Scan for {hero_name} found: {found_header_ranks}")

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

            if not match_found:
                current_rank = found_header_ranks[0][1]
                current_rank_idx = 0
                logger.debug(
                    f"No consensus for {hero_name}: fallback to {current_rank}."
                )

            if len(found_header_ranks) > current_rank_idx + 1:
                future_rank = found_header_ranks[current_rank_idx + 1][1]

        if future_rank != "Unknown":
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

        do_fallback = current_rank == "Unknown" or any(
            kw in current_rank.lower() for kw in ["supreme", "mythic", "paragon"]
        )

        combined_context = (full_line_text + " " + stats_text).upper()
        if do_fallback:
            rank_patterns = [
                (r"PARAGON (\d)", lambda m: f"Paragon {m.group(1)}"),
                (r"SUPREME[\s]*[\+t\*kåvfi1l|]", "Supreme+"),
                (r"SUPREME", "Supreme"),
                (r"MYTHIC[\s]*[\+t\*kåvfi1l|]", "Mythic+"),
                (r"MYTHIC", "Mythic"),
                (r"LEGENDARY[\s]*[\+t\*kåvfi1l|]", "Legendary+"),
                (r"LEGENDARY", "Legendary"),
                (r"EPIC[\s]*[\+t\*kåvfi1l|]", "Epic+"),
                (r"EPIC", "Epic"),
            ]

            found_ranks = []
            for pattern, rank_val in rank_patterns:
                match = re.search(pattern, combined_context, re.IGNORECASE)
                if match:
                    val_str = rank_val if isinstance(rank_val, str) else rank_val(match)
                    found_ranks.append((match.start(), val_str))

            if found_ranks:
                found_ranks.sort(key=lambda x: (x[0], -len(x[1])))

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

        has_rivalry = "RIVALRY" in stats_text.upper()

        if has_rivalry:
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

    # ------------------------------------------------------------------
    # Screen processing
    # ------------------------------------------------------------------

    def _get_precise_name_crop(self, screenshot: np.ndarray) -> np.ndarray:
        roi_y_start, roi_y_end = 60, 200
        roi_x_start, roi_x_end = 110, 950
        wide_crop = screenshot[roi_y_start:roi_y_end, roi_x_start:roi_x_end]

        gray = cv2.cvtColor(wide_crop, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        candidates = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if h > 40 and w > 10:  # noqa: PLR2004
                candidates.append((x, y, x + w, y + h))

        if not candidates:
            return wide_crop

        min_x = min(c[0] for c in candidates)
        min_y = min(c[1] for c in candidates)
        max_x = max(c[2] for c in candidates)
        max_y = max(c[3] for c in candidates)

        pad = 20
        p_x = max(0, min_x - pad)
        p_y = max(0, min_y - pad)
        p_w = min(wide_crop.shape[1] - p_x, (max_x - min_x) + pad * 2)
        p_h = min(wide_crop.shape[0] - p_y, (max_y - min_y) + pad * 2)

        return wide_crop[p_y : p_y + p_h, p_x : p_x + p_w]

    def _process_hero_screen(self, screenshot: np.ndarray) -> dict:
        """Extract name, ascension and EX level from a hero detail screen."""
        crop_asc = (5, 5, 130, 170)
        crop_ex = (10, 1400, 450, 1650)

        name_img = self._get_precise_name_crop(screenshot)
        name_img_scaled = cv2.resize(
            name_img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
        )
        gray_name = cv2.cvtColor(name_img_scaled, cv2.COLOR_BGR2GRAY)

        raw_name_a = self._ocr_text_rapid(gray_name)

        _, thresh_name = cv2.threshold(
            gray_name, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        raw_name_b = self._ocr_text_rapid(thresh_name)

        kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        sharpened_name = cv2.filter2D(gray_name, -1, kernel)
        raw_name_c = self._ocr_text_rapid(sharpened_name)

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
        raw_asc = self._ocr_text_rapid(asc_img_scaled)

        ex_img = screenshot[crop_ex[1] : crop_ex[3], crop_ex[0] : crop_ex[2]]
        ex_img_scaled = cv2.resize(
            ex_img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
        )
        gray_ex = cv2.cvtColor(ex_img_scaled, cv2.COLOR_BGR2GRAY)

        _, thresh_a = cv2.threshold(
            gray_ex, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
        raw_ex_a = self._ocr_text_rapid(thresh_a)

        _, thresh_b = cv2.threshold(
            gray_ex, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        raw_ex_b = self._ocr_text_rapid(thresh_b)

        raw_ex_combined = f"{raw_ex_a} {raw_ex_b}"

        ascension = self._match_ascension(raw_asc)
        ex = self._parse_ex_level(raw_ex_combined, ascension, name)
        raw_name = " | ".join(raw_names)

        return {
            "name": name,
            "raw_name": raw_name,
            "raw_asc": raw_asc,
            "ascension": ascension,
            "ex_weapon": ex,
            "raw_ex": raw_ex_combined,
        }

    # ------------------------------------------------------------------
    # Hero name matching
    # ------------------------------------------------------------------

    def _prepare_hero_matching_data(
        self, raw_input: str | list[str]
    ) -> tuple[list[str], str, list[dict], list[str]]:
        if isinstance(raw_input, list):
            readings = [r for r in raw_input if r.strip()]
            raw_text = " ".join(readings)
        else:
            readings = [raw_input]
            raw_text = raw_input

        hero_meta = []
        for h in self.canonical_hero_names:
            norm = re.sub(r"[^a-zA-Z0-9]", "", h).lower().replace("and", "")
            h_tokens = [
                re.sub(r"[^a-zA-Z0-9]", "", t).lower()
                for t in h.split()
                if len(t) > 2  # noqa: PLR2004
            ]
            hero_meta.append({"name": h, "norm": norm, "tokens": h_tokens})

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
        for h in hero_meta:
            if not h["tokens"]:
                continue
            matches_count = sum(
                1
                for h_token in h["tokens"]
                if any(h_token in ocr_t for ocr_t in all_ocr_tokens)
            )
            if matches_count == len(h["tokens"]):
                logger.debug(f"MATCH STRATEGY: [TOKEN-INTERSECT] -> '{h['name']}'")
                return h["name"]

        for reading in readings:
            reading_clean = re.sub(r"[^a-zA-Z0-9]", "", reading).lower()
            for h in hero_meta:
                if len(h["norm"]) >= 4 and h["norm"] in reading_clean:  # noqa: PLR2004
                    logger.debug(
                        f"MATCH STRATEGY: [INDEPENDENT-SUB]"
                        f" '{reading}' -> '{h['name']}'"
                    )
                    return h["name"]

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
        if not self.hero_synonyms:
            self._load_synonyms()

        synonym_matches = []
        for token in all_ocr_tokens:
            for pattern_raw, canonical in self.hero_synonyms.items():
                pattern = re.sub(r"[^a-zA-Z0-9]", "", pattern_raw).lower()
                if not pattern:
                    continue
                if (len(pattern) < 5 and token == pattern) or (  # noqa: PLR2004
                    len(pattern) >= 5 and pattern in token  # noqa: PLR2004
                ):
                    synonym_matches.append((len(pattern), canonical))

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
        norm_to_canonical = {
            re.sub(r"[^a-zA-Z0-9]", "", name).lower(): name
            for name in self.canonical_hero_names
        }

        if len(text_clean) >= 6:  # noqa: PLR2004
            for norm, canonical in norm_to_canonical.items():
                if text_clean in norm or norm in text_clean:
                    logger.debug(f"MATCH STRATEGY: [SUBSTRING] -> '{canonical}'")
                    return canonical

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
        if not raw_input:
            return "Unknown"

        readings, raw_text, hero_meta, all_ocr_tokens = (
            self._prepare_hero_matching_data(raw_input)
        )
        text_clean = re.sub(r"[^a-zA-Z0-9]", "", raw_text).lower()
        if not text_clean:
            return "Unknown"

        match = self._match_independent_strategies(readings, hero_meta, all_ocr_tokens)
        if not match:
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
            match = self._match_synonym_strategies(raw_text, text_clean, all_ocr_tokens)

        if not match:
            match = self._match_fuzzy_fallback_strategies(text_clean)

        return match or "Unknown"

    # ------------------------------------------------------------------
    # Ascension & EX weapon parsing
    # ------------------------------------------------------------------

    def _match_ascension(self, raw_text: str) -> str:
        if not raw_text:
            return "Unknown"
        text = raw_text.strip()

        best_match = None
        earliest_index = 999

        for pattern, canonical in ASCENSION_OCR_MAP.items():
            idx = text.lower().find(pattern.lower())
            if idx != -1 and idx < earliest_index:
                earliest_index = idx
                best_match = canonical

        if best_match:
            return best_match

        text = text.lower()
        possible_bases = ["Supreme", "Mythic", "Legendary", "Elite", "Epic"]

        found_matches = []
        for base in possible_bases:
            idx = text.find(base.lower())
            if idx != -1:
                found_matches.append((idx, base))

        if found_matches:
            found_matches.sort(key=lambda x: x[0])
            base_rank = found_matches[0][1]

            search_start = text.lower().find(base_rank.lower()) + len(base_rank)
            search_area = text[max(0, search_start) : search_start + 2]

            plus_chars = ["+", "å  "]
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

        cleaned = raw_text.upper()
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

        text_for_plus = (
            cleaned.replace("T", "+")
            .replace("K", "+")
            .replace("V", "+")
            .replace("f", "+")
        )
        plus_matches = re.findall(r"\+\s*([0-9]{1,2})", text_for_plus)
        if plus_matches:
            valid_vals = [int(m) for m in plus_matches if 0 <= int(m) <= 40]  # noqa: PLR2004
            if valid_vals:
                return max(valid_vals)

        if any(
            kw in raw_text.upper()
            for kw in ["LVL", "RES", "RESONANCE", "REA", "REACH", "UNLOCK"]
        ):
            return 0

        lone_nums = re.findall(r"(?<![A-Z0-9])(\d{1,2})(?![A-Z0-9])", cleaned)
        if lone_nums:
            valid_vals = [int(m) for m in lone_nums if 0 <= int(m) <= 40]  # noqa: PLR2004
            if valid_vals:
                return max(valid_vals)

        return 0

    # ------------------------------------------------------------------
    # OCR helpers
    # ------------------------------------------------------------------

    def _ocr_text_rapid(self, image: np.ndarray, crop: tuple | None = None) -> str:
        """Run RapidOCR on an image and return the extracted text.

        Args:
            image: Image to process.
            crop: Unused — kept for signature compatibility.

        Returns:
            Extracted text string.
        """
        if self._rapid_ocr is None:
            self._rapid_ocr = RapidOCR()

        result = self._rapid_ocr(image)
        if result:
            if hasattr(result, "txts") and result.txts:
                return " ".join(str(t) for t in result.txts).strip()  # ty: ignore[not-iterable]

            texts = []
            results_list = result if isinstance(result, list) else [result]
            for line in results_list:
                if isinstance(line, (list, tuple)) and len(line) > 1:
                    texts.append(str(line[1]))
                elif isinstance(line, str):
                    texts.append(line)
            return " ".join(texts).strip()
        return ""

    def _load_synonyms(self) -> None:
        """Load hero synonyms from disk (user-downloaded version preferred)."""
        self.hero_synonyms = {}

        data_root = SettingsLoader.get_app_config_dir()
        user_synonym_path = data_root / "data" / "hero_synonyms.json"
        project_root = self._get_project_root()
        bundled_synonym_path = project_root / "data" / "hero_synonyms.json"

        for synonym_path in [user_synonym_path, bundled_synonym_path]:
            if synonym_path.exists():
                try:
                    with open(synonym_path, encoding="utf-8") as f:
                        self.hero_synonyms = json.load(f)
                    logger.debug(
                        f"Loaded {len(self.hero_synonyms)} hero name synonyms"
                        f" from {synonym_path}."
                    )
                    return
                except Exception as e:
                    logger.error(f"Failed to load synonyms from {synonym_path}: {e}")

        logger.warning("No synonym files found.")

    def _get_project_root(self) -> Path:
        try:
            resource_dir = SettingsLoader.get_resource_dir()
            if "src-python" in resource_dir.parts:
                try:
                    p_idx = resource_dir.parts.index("src-python")
                    if p_idx > 0 and resource_dir.parts[p_idx - 1] == "src-tauri":
                        return Path(*resource_dir.parts[: p_idx - 1])
                    return Path(*resource_dir.parts[:p_idx])
                except (ValueError, IndexError):
                    pass
            return resource_dir
        except Exception:
            return Path(__file__).parents[6]
