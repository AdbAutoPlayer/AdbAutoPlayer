"""Guild scan: Dream Realm and Supreme Arena rankings scanning."""

import datetime
import json
import logging
import os
import re
from time import sleep

import cv2
from adb_auto_player.exceptions import AutoPlayerWarningError, GameTimeoutError
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.ocr import OCRResult
from adb_auto_player.ocr import OCRBackend, RapidOCRBackend
from adb_auto_player.ocr.qwen2vl_backend import QwenVLOCRBackend

from ._guild_scan_names import _GuildScanNamesMixin


class _GuildScanRankingsMixin(_GuildScanNamesMixin):
    """Dream Realm and Supreme Arena rankings scanning and OCR parsing."""

    def _run_dream_realm_scan(
        self,
        ocr_backend: OCRBackend,
        fallback: OCRBackend | None,
        guild_members: list[str],
    ) -> list[dict]:
        """Enter Dream Realm, select district rankings, scan configured dates."""
        self._enter_dr()

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

        if not self._select_district_rankings(ocr_backend):
            raise AutoPlayerWarningError("Failed to select District Rankings tab.")

        processed_dates: set[str] = set()
        dates_to_scan = self.settings.guild_manager_scan.days_to_scan
        rankings: list[dict] = []

        today = datetime.datetime.now().strftime("%A")
        ignore_days = self.settings.guild_manager_scan.ignore_day_restrictions
        scan_today = self.settings.guild_manager_scan.scan_dr_today_on_sunday
        skip_today = not (scan_today and (today == "Sunday" or ignore_days))

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

                self.tap(tab.box.center)
                sleep(2)

                if not self._set_guild_members_filter(ocr_backend):
                    logging.warning(
                        "Could not set filter to Guild Members. "
                        "Rankings may contain all players."
                    )

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

                weekday_name = self._date_to_english_weekday(date_name)
                logging.info(f"Converted date {date_name} to weekday {weekday_name}")

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
        if "not" in text_lower:
            return False
        return True

    def _set_guild_members_filter(self, ocr_backend: OCRBackend) -> bool:
        logging.info("Setting filter to Guild Members...")

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
        y_min = self._Y_MIN_RANKINGS
        if is_supreme_arena:
            y_min = 700
        elif is_first_frame:
            y_min = 820

        if isinstance(ocr_backend, QwenVLOCRBackend):
            h = screenshot.shape[0]
            backend_name = "qwen2vl"
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
                if is_supreme_arena and not is_first_frame:
                    supplemental = [r for r in supplemental if r[0] is not None]

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
        seen_ranks: dict[str, tuple] = {}
        deduped: list[tuple] = []
        for rk, nm, sc in corrected:
            if not rk or rk not in seen_ranks:
                deduped.append((rk, nm, sc))
                if rk:
                    seen_ranks[rk] = (rk, nm, sc)
            elif nm and nm in name_rank:
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
            if matched is None:
                matched_fuzzy = self._correct_single_name(recovered, list(guild_set))
                if matched_fuzzy != recovered:
                    matched = matched_fuzzy
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

        logging.info("Tapping Rankings button in Supreme Arena...")
        try:
            reward = self.wait_for_template(
                "supreme_arena/rankings.png",
                timeout_message=("Could not find Rankings button in Supreme Arena."),
                timeout=self.min_timeout,
            )
            self.tap(reward)
            sleep(2)
        except GameTimeoutError:
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
                logging.warning(
                    "Could not find rankings button template, trying OCR..."
                )
            screenshot = self.get_screenshot()
            ocr_results = ocr_backend.detect_text_blocks(screenshot)
            found = False
            for res in ocr_results:
                text = res.text.lower()
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

        if not self._set_guild_members_filter(ocr_backend):
            logging.warning(
                "Could not set filter to Guild Members. "
                "Rankings may contain all players."
            )

        scroll_top_btn = self.game_find_template_match(
            "dream_realm/scroll_top.png",
            threshold=ConfidenceValue("80%"),
        )
        if scroll_top_btn:
            logging.info("Found scroll-to-top button, tapping to reset list to top.")
            self.tap(scroll_top_btn.box.center)
            sleep(2)

        day_name = datetime.datetime.now().strftime("%A")
        logging.info(f"Scanning Supreme Arena rankings for {day_name}...")

        sa_rankings = self._scan_rankings_for_current_date(
            day_name, ocr_backend, fallback, is_supreme_arena=True
        )
        sa_rankings = self._correct_names_with_guild_members(
            sa_rankings, guild_members or []
        )

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
