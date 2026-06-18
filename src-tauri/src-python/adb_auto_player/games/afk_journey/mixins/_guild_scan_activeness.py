"""Guild scan: activeness and chest contribution scanning."""

import logging
import os
import re
from difflib import SequenceMatcher
from time import sleep

from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.models.geometry import Point
from adb_auto_player.ocr import OCRBackend, RapidOCRBackend
from adb_auto_player.ocr.qwen2vl_backend import QwenVLOCRBackend

from ._guild_scan_rankings import _GuildScanRankingsMixin


class _GuildScanActivenessMixin(_GuildScanRankingsMixin):
    """Guild activeness and chest contribution scanning."""

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

        logging.info("Swiping to reveal Members button...")
        self.device.swipe(
            Point(self._GUILD_SWIPE_SX, self._GUILD_SWIPE_SY),
            Point(self._GUILD_SWIPE_EX, self._GUILD_SWIPE_EY),
            duration=0.6,
        )
        sleep(1.5)

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
                logging.warning("Members button not found, swiping again to reveal it.")
                self.device.swipe(
                    Point(self._GUILD_SWIPE_SX, self._GUILD_SWIPE_SY),
                    Point(self._GUILD_SWIPE_EX, self._GUILD_SWIPE_EY),
                    duration=0.6,
                )
                sleep(1.5)

        logging.error("Members button not found after multiple attempts.")
        return False

    _RE_POWER_RATING = re.compile(
        r"^\d+[.,]?\d*\s*[KMBkmb]\b",
        re.IGNORECASE,
    )
    _RE_BASE_SUFFIX = re.compile(
        r"[(" + chr(0xFF08) + r"]\s*[Bb]ase\s*[)" + chr(0xFF09) + r"]"
    )
    _RE_GUILD_HEADER = re.compile(
        r"guild\s*member",
        re.IGNORECASE,
    )
    _MAX_NUMERIC_NAME_DIGITS = 4

    def _is_valid_activeness_name(self, text: str) -> bool:
        """Return True only when `text` looks like a real player name."""
        t = text.strip()
        if len(t) < self._MIN_NAME_LENGTH:
            return False
        if self._RE_POWER_RATING.match(t) or self._RE_BASE_SUFFIX.search(t):
            return False
        if self._RE_GUILD_HEADER.search(t):
            return False
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
        """Parse (name, activeness_value) pairs from the guild members list screen."""
        ocr_results = ocr_backend.detect_text_blocks(screenshot)

        area_blocks = [
            res
            for res in ocr_results
            if self._Y_ACTIVENESS_MIN <= res.box.center.y <= self._Y_ACTIVENESS_MAX
        ]

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

        name_blocks.sort(key=lambda b: b.box.center.y)

        pairs: list[tuple[str | None, str | None]] = []
        used_activeness_indices: set[int] = set()

        for nb in name_blocks:
            name_y = nb.box.center.y

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
        """Ask Qwen to name-read rows whose activeness value has no paired name."""
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
            if (
                t.isdigit()
                and int(t) <= self._MAX_CHEST_RANK_NUMBER
                and b.box.center.x < self._X_CHEST_RANK_BADGE_MAX
            ):
                continue
            name_blocks.append(b)

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
        nav_backend = RapidOCRBackend()
        self._activeness_qwen: QwenVLOCRBackend | None = (
            ocr_backend if isinstance(ocr_backend, QwenVLOCRBackend) else None
        )

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
        dedup: dict[str, dict] = {}
        for entry in corrected:
            key = entry["Name"]
            if key not in dedup or entry["Activeness"] > dedup[key]["Activeness"]:
                dedup[key] = entry
        return list(dedup.values())

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
                import json  # noqa: PLC0415

                json.dump(records, f, indent=4, ensure_ascii=False)
            logging.info(
                f"Successfully exported {len(records)} guild activeness entries."
            )
            logging.info(f"Output file path: {output_file}")
        except Exception as e:
            logging.error(f"Failed to save guild activeness JSON: {e}")
