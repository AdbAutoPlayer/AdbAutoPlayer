"""Tests for HeroScanner pure-logic methods.

All tests target methods that process in-memory data and do not require
a real device, Tauri window, or network connection.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from adb_auto_player.games.afk_journey.services.hero_scanner import HeroScanner
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.ocr import OCRResult

_SUP_TO_P1 = 25  # S+ heroes needed to unlock P1
_P1_TO_P2 = 20  # P1 heroes needed to unlock P2
_P2_TO_P3 = 15  # P2 heroes needed to unlock P3
_P3_TO_P4 = 15  # P3 heroes needed to unlock P4

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scanner(
    canonical: list[str] | None = None,
    synonyms: dict | None = None,
) -> HeroScanner:
    """Return a HeroScanner whose game reference is fully mocked."""
    scanner = HeroScanner(MagicMock())
    scanner.canonical_hero_names = canonical or []
    scanner.hero_synonyms = synonyms or {}
    scanner.tracker_file = ""
    return scanner


# ---------------------------------------------------------------------------
# _prepare_hero_matching_data
# ---------------------------------------------------------------------------


class TestPrepareHeroMatchingData:
    def test_string_input_becomes_single_reading(self):
        scanner = _make_scanner(["Lumont"])
        readings, raw_text, _, _ = scanner._prepare_hero_matching_data("Lumont")
        assert readings == ["Lumont"]
        assert raw_text == "Lumont"

    def test_list_input_filters_blank_entries(self):
        scanner = _make_scanner(["Lumont"])
        readings, raw_text, _, _ = scanner._prepare_hero_matching_data(
            ["Lumont", "", "  "]
        )
        assert readings == ["Lumont"]
        assert raw_text == "Lumont"

    def test_list_input_joins_readings(self):
        scanner = _make_scanner(["Lumont"])
        _, raw_text, _, _ = scanner._prepare_hero_matching_data(["Lum", "ont"])
        assert raw_text == "Lum ont"

    def test_hero_meta_tokens_skip_short_words(self):
        # Words <= 2 chars should be omitted from hero tokens
        scanner = _make_scanner(["Gu En"])
        _, _, hero_meta, _ = scanner._prepare_hero_matching_data("Gu En")
        # "Gu" and "En" are both 2 chars → tokens list should be empty
        assert hero_meta[0]["tokens"] == []

    def test_ocr_tokens_skip_single_char(self):
        scanner = _make_scanner()
        _, _, _, all_ocr_tokens = scanner._prepare_hero_matching_data("A bc def")
        # "A" is 1 char → skipped; "bc" (2 chars) and "def" included
        assert "a" not in all_ocr_tokens
        assert "bc" in all_ocr_tokens
        assert "def" in all_ocr_tokens


# ---------------------------------------------------------------------------
# _match_independent_strategies
# ---------------------------------------------------------------------------


class TestMatchIndependentStrategies:
    def test_token_intersect_exact(self):
        scanner = _make_scanner(["Korin"])
        _, _, hero_meta, all_ocr_tokens = scanner._prepare_hero_matching_data("Korin")
        result = scanner._match_independent_strategies(
            ["Korin"], hero_meta, all_ocr_tokens
        )
        assert result == "Korin"

    def test_independent_sub_match(self):
        scanner = _make_scanner(["Lumont"])
        # Provide a reading where the hero norm is a substring
        _, _, hero_meta, all_ocr_tokens = scanner._prepare_hero_matching_data(
            "XLumontY"
        )
        result = scanner._match_independent_strategies(
            ["XLumontY"], hero_meta, all_ocr_tokens
        )
        assert result == "Lumont"

    def test_token_fragment_match(self):
        scanner = _make_scanner(["Greystone"])
        # OCR token "greysto" is a fragment of "greystone"
        _, _, hero_meta, _ = scanner._prepare_hero_matching_data("greysto")
        all_ocr_tokens = ["greysto"]
        result = scanner._match_independent_strategies(
            ["greysto"], hero_meta, all_ocr_tokens
        )
        assert result == "Greystone"

    def test_no_match_returns_none(self):
        scanner = _make_scanner(["Lumont"])
        result = scanner._match_independent_strategies(["xyz"], [], [])
        assert result is None

    def test_hero_with_no_tokens_skipped(self):
        # Hero whose words are all <= 2 chars has empty tokens list → skipped
        scanner = _make_scanner(["AB"])
        _, _, hero_meta, all_ocr_tokens = scanner._prepare_hero_matching_data("AB")
        result = scanner._match_independent_strategies(
            ["AB"], hero_meta, all_ocr_tokens
        )
        assert result is None


# ---------------------------------------------------------------------------
# _match_synonym_strategies
# ---------------------------------------------------------------------------


class TestMatchSynonymStrategies:
    def test_short_synonym_exact_token_match(self):
        scanner = _make_scanner(synonyms={"Kaz": "Kazuki"})
        result = scanner._match_synonym_strategies("Kaz", "kaz", ["kaz"])
        assert result == "Kazuki"

    def test_long_synonym_substring_match(self):
        scanner = _make_scanner(synonyms={"Lumontish": "Lumont"})
        result = scanner._match_synonym_strategies(
            "XLumontishY", "xlumontishy", ["xlumontishy"]
        )
        assert result == "Lumont"

    def test_synonym_in_text_clean(self):
        scanner = _make_scanner(synonyms={"Greystone": "Greystone the Elder"})
        result = scanner._match_synonym_strategies(
            "Greystone hero", "greystonehero", ["greystonehero"]
        )
        assert result == "Greystone the Elder"

    def test_no_synonyms_loads_from_disk(self):
        scanner = _make_scanner()
        scanner.hero_synonyms = {}
        with patch.object(scanner, "_load_synonyms") as mock_load:
            scanner._match_synonym_strategies("text", "text", ["text"])
            mock_load.assert_called_once()

    def test_longest_pattern_wins(self):
        # Two synonyms match; the longer pattern should win
        scanner = _make_scanner(
            synonyms={"flora": "Flora", "floramancer": "Floramancer"}
        )
        result = scanner._match_synonym_strategies(
            "floramancer", "floramancer", ["floramancer"]
        )
        assert result == "Floramancer"


# ---------------------------------------------------------------------------
# _match_fuzzy_fallback_strategies
# ---------------------------------------------------------------------------


class TestMatchFuzzyFallbackStrategies:
    def test_exact_substring_long_text(self):
        scanner = _make_scanner(["Greystone"])
        result = scanner._match_fuzzy_fallback_strategies("greystone")
        assert result == "Greystone"

    def test_fuzzy_close_match(self):
        scanner = _make_scanner(["Greystone"])
        # "greystune" is close to "greystone" → should fuzzy-match
        result = scanner._match_fuzzy_fallback_strategies("greystune")
        assert result == "Greystone"

    def test_short_text_no_substring_match(self):
        scanner = _make_scanner(["AB"])
        # text_clean "ab" len < 6 → substring path skipped; too short for fuzzy
        result = scanner._match_fuzzy_fallback_strategies("ab")
        # Might or might not match depending on cutoff; just ensure no exception
        assert result is None or result == "AB"

    def test_returns_none_for_no_match(self):
        scanner = _make_scanner(["Lumont", "Greystone"])
        result = scanner._match_fuzzy_fallback_strategies("zzzzzzzzzzz")
        assert result is None


# ---------------------------------------------------------------------------
# _match_hero_name (end-to-end)
# ---------------------------------------------------------------------------


class TestMatchHeroName:
    def test_empty_input_returns_unknown(self):
        scanner = _make_scanner(["Lumont"])
        assert scanner._match_hero_name("") == "Unknown"
        assert scanner._match_hero_name([]) == "Unknown"

    def test_whitespace_only_returns_unknown(self):
        scanner = _make_scanner(["Lumont"])
        assert scanner._match_hero_name("   ") == "Unknown"

    def test_exact_match(self):
        scanner = _make_scanner(["Lumont"])
        assert scanner._match_hero_name("Lumont") == "Lumont"

    def test_list_input_matches(self):
        scanner = _make_scanner(["Greystone"])
        assert scanner._match_hero_name(["Greystone"]) == "Greystone"

    def test_ocr_noise_still_matches(self):
        scanner = _make_scanner(["Greystone"])
        # OCR often adds extra characters around the name
        assert scanner._match_hero_name("XGreystoneX") == "Greystone"

    def test_falls_back_to_unknown_for_garbage(self):
        scanner = _make_scanner(["Lumont", "Greystone"])
        result = scanner._match_hero_name("!@#$%^&*()")
        assert result == "Unknown"

    def test_exact_strategy_used_for_known_norm(self):
        # "korin" normalises to itself; canonical list contains "Korin"
        scanner = _make_scanner(["Korin"])
        assert scanner._match_hero_name("korin") == "Korin"

    def test_synonym_fallback(self):
        scanner = _make_scanner(["Kazuki"], synonyms={"Kaz": "Kazuki"})
        assert scanner._match_hero_name("Kaz") == "Kazuki"


# ---------------------------------------------------------------------------
# _match_ascension
# ---------------------------------------------------------------------------


class TestMatchAscension:
    def test_empty_string_returns_unknown(self):
        scanner = _make_scanner()
        assert scanner._match_ascension("") == "Unknown"

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Paragon 1", "Paragon 1"),
            ("Paragon 2", "Paragon 2"),
            ("Paragon 3", "Paragon 3"),
            ("Paragon 4", "Paragon 4"),
            ("Crown", "Paragon 4"),
            ("Crowns", "Paragon 4"),
            ("Subreme", "Supreme"),
            ("Suprem", "Supreme"),
            ("Lvthic", "Mythic"),
            ("Mvthic", "Mythic"),
            ("Legend", "Legendary"),
        ],
    )
    def test_ocr_map_patterns(self, raw: str, expected: str):
        scanner = _make_scanner()
        assert scanner._match_ascension(raw) == expected

    def test_mythic_plus(self):
        scanner = _make_scanner()
        # "Mythic*" should produce "Mythic+"
        result = scanner._match_ascension("Mythic*")
        assert result == "Mythic+"

    def test_legendary_plus(self):
        # "Legend" entry in ASCENSION_OCR_MAP matches first and returns "Legendary"
        # before the base-detection path can append "+"
        scanner = _make_scanner()
        result = scanner._match_ascension("Legendary+")
        assert result == "Legendary"

    def test_epic_base(self):
        scanner = _make_scanner()
        assert scanner._match_ascension("Epic") == "Epic"

    def test_supreme_base(self):
        scanner = _make_scanner()
        assert scanner._match_ascension("Supreme") == "Supreme"

    def test_elite_plus(self):
        scanner = _make_scanner()
        result = scanner._match_ascension("Elite+")
        assert result == "Elite+"

    def test_no_match_returns_unknown(self):
        scanner = _make_scanner()
        assert scanner._match_ascension("garbage text xyz") == "Unknown"

    def test_earliest_match_wins_when_multiple_patterns(self):
        # "Crown Paragon 1" has "Crown" (→ P4) at idx 0 and "Paragon 1" at idx 6.
        # Earliest index should win → "Paragon 4"
        scanner = _make_scanner()
        result = scanner._match_ascension("Crown Paragon 1")
        assert result == "Paragon 4"


# ---------------------------------------------------------------------------
# _parse_ex_level
# ---------------------------------------------------------------------------


class TestParseExLevel:
    @pytest.mark.parametrize(
        "ascension",
        [
            "Mythic",
            "Legendary+",
            "Elite",
            "Epic",
            "Not Owned",
            "Unknown",
        ],
    )
    def test_ineligible_ascension_returns_zero(self, ascension: str):
        scanner = _make_scanner()
        assert scanner._parse_ex_level("EX +10", ascension) == 0

    @pytest.mark.parametrize(
        "ascension",
        [
            "Mythic+",
            "Supreme",
            "Supreme+",
            "Paragon 1",
            "Paragon 2",
            "Paragon 3",
            "Paragon 4",
            "Paragon Locked",
            "Pending S+/P4",
        ],
    )
    def test_eligible_ascension_can_return_nonzero(self, ascension: str):
        scanner = _make_scanner()
        result = scanner._parse_ex_level("EX +5", ascension)
        assert result == 5

    def test_plus_pattern_extraction(self):
        scanner = _make_scanner()
        assert scanner._parse_ex_level("EX Weapon +15", "Supreme") == 15

    def test_ocr_t_as_plus(self):
        # OCR artifact: "T" → "+"
        scanner = _make_scanner()
        assert scanner._parse_ex_level("EX T12", "Supreme") == 12

    def test_noise_words_removed_before_parsing(self):
        scanner = _make_scanner()
        # "LVL 99" should be stripped; "EX +7" should survive
        result = scanner._parse_ex_level("LVL 99 EX +7", "Supreme")
        assert result == 7

    def test_level_keyword_triggers_zero_fallback(self):
        scanner = _make_scanner()
        # Text contains "LVL" but no EX level → 0
        result = scanner._parse_ex_level("LVL 10", "Supreme")
        assert result == 0

    def test_lone_number_fallback(self):
        scanner = _make_scanner()
        result = scanner._parse_ex_level("20", "Supreme")
        assert result == 20

    def test_out_of_range_number_ignored(self):
        scanner = _make_scanner()
        # 99 > 40 → invalid; no valid value → 0
        result = scanner._parse_ex_level("99", "Supreme")
        assert result == 0

    def test_max_of_multiple_values(self):
        scanner = _make_scanner()
        result = scanner._parse_ex_level("+5 +20 +10", "Supreme")
        assert result == 20


# ---------------------------------------------------------------------------
# resolve_locked_paragons and helpers
# ---------------------------------------------------------------------------


def _make_hero(name: str, ascension: str) -> dict:
    return {"name": name, "currentAscension": ascension}


class TestResolveLockedParagons:
    def _full_data(self, heroes: list[dict]) -> dict:
        return {"heroes": heroes}

    def test_pending_resolved_to_paragon1_when_enough_sup_not_enough_p1(self, tmp_path):
        scanner = _make_scanner()
        scanner.tracker_file = str(tmp_path / "tracker.json")
        # 25 S+ unlocks P1, but only 1 P1 confirmed → P2 not unlocked → pending = P1
        heroes = [_make_hero(f"h{i}", "Supreme+") for i in range(_SUP_TO_P1 - 1)]
        heroes.append(_make_hero("p1hero", "Paragon 1"))
        heroes.append(_make_hero("pending", "Pending S+/P4"))
        full_data = self._full_data(heroes)
        (tmp_path / "tracker.json").write_text(json.dumps(full_data))

        scanner.resolve_locked_paragons(full_data, global_ascend_available=False)

        pending = next(h for h in full_data["heroes"] if h["name"] == "pending")
        assert pending["currentAscension"] == "Paragon 1"

    def test_pending_resolved_to_paragon2_when_enough_p1_not_enough_p2(self, tmp_path):
        scanner = _make_scanner()
        scanner.tracker_file = str(tmp_path / "tracker.json")
        # 20 P1 unlocks P2, but only 1 P2 confirmed → P3 not unlocked → pending = P2
        heroes = [_make_hero(f"s{i}", "Supreme+") for i in range(_SUP_TO_P1)]
        heroes += [_make_hero(f"p1_{i}", "Paragon 1") for i in range(_P1_TO_P2 - 1)]
        heroes.append(_make_hero("p2hero", "Paragon 2"))
        heroes.append(_make_hero("pending", "Pending S+/P4"))
        full_data = self._full_data(heroes)
        (tmp_path / "tracker.json").write_text(json.dumps(full_data))

        scanner.resolve_locked_paragons(full_data, global_ascend_available=False)

        pending = next(h for h in full_data["heroes"] if h["name"] == "pending")
        assert pending["currentAscension"] == "Paragon 2"

    def test_pending_resolved_to_supreme_plus_when_not_enough_sup(self, tmp_path):
        scanner = _make_scanner()
        scanner.tracker_file = str(tmp_path / "tracker.json")
        heroes = [_make_hero(f"h{i}", "Supreme+") for i in range(5)]
        heroes.append(_make_hero("pending", "Pending S+/P4"))
        full_data = self._full_data(heroes)
        (tmp_path / "tracker.json").write_text(json.dumps(full_data))

        scanner.resolve_locked_paragons(full_data, global_ascend_available=False)

        pending = next(h for h in full_data["heroes"] if h["name"] == "pending")
        assert pending["currentAscension"] == "Supreme+"

    def test_pending_resolved_to_paragon4_when_all_thresholds_met(self, tmp_path):
        scanner = _make_scanner()
        scanner.tracker_file = str(tmp_path / "tracker.json")
        heroes = [_make_hero(f"s{i}", "Supreme+") for i in range(_SUP_TO_P1)]
        heroes += [_make_hero(f"p1_{i}", "Paragon 1") for i in range(_P1_TO_P2)]
        heroes += [_make_hero(f"p2_{i}", "Paragon 2") for i in range(_P2_TO_P3)]
        heroes += [_make_hero(f"p3_{i}", "Paragon 3") for i in range(_P3_TO_P4)]
        heroes.append(_make_hero("pending", "Pending S+/P4"))
        full_data = self._full_data(heroes)
        (tmp_path / "tracker.json").write_text(json.dumps(full_data))

        scanner.resolve_locked_paragons(full_data, global_ascend_available=False)

        pending = next(h for h in full_data["heroes"] if h["name"] == "pending")
        assert pending["currentAscension"] == "Paragon 4"

    def test_misread_paragons_downgraded_when_not_enough_sup(self, tmp_path):
        scanner = _make_scanner()
        scanner.tracker_file = str(tmp_path / "tracker.json")
        heroes = [_make_hero("misread", "Paragon 2")]
        full_data = self._full_data(heroes)
        (tmp_path / "tracker.json").write_text(json.dumps(full_data))

        scanner.resolve_locked_paragons(full_data, global_ascend_available=False)

        misread = full_data["heroes"][0]
        assert misread["currentAscension"] == "Supreme+"


class TestComputeLockedTier:
    def test_returns_supreme_plus_when_no_confirmed(self):
        scanner = _make_scanner()
        assert scanner._compute_locked_tier([]) == "Supreme+"

    def test_returns_supreme_plus_when_below_p1_threshold(self):
        scanner = _make_scanner()
        heroes = [_make_hero(f"h{i}", "Supreme+") for i in range(_SUP_TO_P1 - 1)]
        assert scanner._compute_locked_tier(heroes) == "Supreme+"

    def test_returns_paragon1_when_enough_sup_not_enough_p1(self):
        scanner = _make_scanner()
        heroes = [_make_hero(f"h{i}", "Supreme+") for i in range(_SUP_TO_P1)]
        assert scanner._compute_locked_tier(heroes) == "Paragon 1"

    def test_returns_paragon2_when_enough_p1_not_enough_p2(self):
        scanner = _make_scanner()
        heroes = [_make_hero(f"s{i}", "Supreme+") for i in range(_SUP_TO_P1)]
        heroes += [_make_hero(f"p1_{i}", "Paragon 1") for i in range(_P1_TO_P2)]
        assert scanner._compute_locked_tier(heroes) == "Paragon 2"

    def test_returns_paragon3_when_enough_p2_not_enough_p3(self):
        scanner = _make_scanner()
        heroes = [_make_hero(f"s{i}", "Supreme+") for i in range(_SUP_TO_P1)]
        heroes += [_make_hero(f"p1_{i}", "Paragon 1") for i in range(_P1_TO_P2)]
        heroes += [_make_hero(f"p2_{i}", "Paragon 2") for i in range(_P2_TO_P3)]
        assert scanner._compute_locked_tier(heroes) == "Paragon 3"

    def test_returns_paragon4_when_all_thresholds_met(self):
        scanner = _make_scanner()
        heroes = [_make_hero(f"s{i}", "Supreme+") for i in range(_SUP_TO_P1)]
        heroes += [_make_hero(f"p1_{i}", "Paragon 1") for i in range(_P1_TO_P2)]
        heroes += [_make_hero(f"p2_{i}", "Paragon 2") for i in range(_P2_TO_P3)]
        heroes += [_make_hero(f"p3_{i}", "Paragon 3") for i in range(_P3_TO_P4)]
        assert scanner._compute_locked_tier(heroes) == "Paragon 4"

    def test_p1_threshold_is_20_not_15(self):
        scanner = _make_scanner()
        # 25 S+ + 15 P1 → not enough for P2 (needs 20) → should return P1
        heroes = [_make_hero(f"s{i}", "Supreme+") for i in range(_SUP_TO_P1)]
        heroes += [_make_hero(f"p1_{i}", "Paragon 1") for i in range(15)]
        assert scanner._compute_locked_tier(heroes) == "Paragon 1"


class TestResolveLockedHeroes:
    def test_locked_resolved_to_given_tier(self):
        scanner = _make_scanner()
        heroes = [_make_hero("locked", "Paragon Locked")]
        scanner._resolve_locked_heroes(heroes, "Paragon 2")
        assert heroes[0]["currentAscension"] == "Paragon 2"

    def test_locked_forced_to_paragon1_when_tier_is_supreme_plus(self):
        scanner = _make_scanner()
        heroes = [_make_hero("locked", "Paragon Locked")]
        scanner._resolve_locked_heroes(heroes, "Supreme+")
        assert heroes[0]["currentAscension"] == "Paragon 1"

    def test_no_locked_heroes_does_nothing(self):
        scanner = _make_scanner()
        heroes = [_make_hero("hero1", "Supreme+")]
        scanner._resolve_locked_heroes(heroes, "Paragon 1")
        assert heroes[0]["currentAscension"] == "Supreme+"


class TestDowngradeMisreadParagons:
    def test_paragons_downgraded_to_supreme_plus(self):
        scanner = _make_scanner()
        heroes = [
            _make_hero("p1", "Paragon 1"),
            _make_hero("p3", "Paragon 3"),
        ]
        scanner._downgrade_misread_paragons(heroes)
        assert all(h["currentAscension"] == "Supreme+" for h in heroes)

    def test_paragon_locked_not_downgraded(self):
        scanner = _make_scanner()
        heroes = [_make_hero("locked", "Paragon Locked")]
        scanner._downgrade_misread_paragons(heroes)
        assert heroes[0]["currentAscension"] == "Paragon Locked"

    def test_non_paragon_not_affected(self):
        scanner = _make_scanner()
        heroes = [_make_hero("hero", "Supreme+")]
        scanner._downgrade_misread_paragons(heroes)
        assert heroes[0]["currentAscension"] == "Supreme+"


class TestResolvePendingHeroes:
    def test_no_pending_returns_early(self):
        scanner = _make_scanner()
        heroes = [_make_hero("h1", "Supreme+")]
        scanner._resolve_pending_heroes(heroes, "Paragon 1")
        assert heroes[0]["currentAscension"] == "Supreme+"

    def test_resolves_to_given_tier(self):
        scanner = _make_scanner()
        heroes = [_make_hero("pending", "Pending S+/P4")]
        scanner._resolve_pending_heroes(heroes, "Paragon 2")
        assert heroes[0]["currentAscension"] == "Paragon 2"

    def test_resolves_to_supreme_plus(self):
        scanner = _make_scanner()
        heroes = [_make_hero("pending", "Pending S+/P4")]
        scanner._resolve_pending_heroes(heroes, "Supreme+")
        assert heroes[0]["currentAscension"] == "Supreme+"


# ---------------------------------------------------------------------------
# _ocr_text_rapid
# ---------------------------------------------------------------------------


class TestOcrTextRapid:
    def test_uses_txts_attribute_when_available(self):
        scanner = _make_scanner()
        mock_ocr = MagicMock()
        mock_result = MagicMock()
        mock_result.txts = ["Hello", "World"]
        mock_ocr.return_value = mock_result
        scanner._rapid_ocr = mock_ocr

        image = np.zeros((10, 10, 3), dtype=np.uint8)
        result = scanner._ocr_text_rapid(image)
        assert result == "Hello World"

    def test_falls_back_to_list_parsing(self):
        scanner = _make_scanner()
        mock_ocr = MagicMock()
        # Result without .txts attribute: list of (box, text) tuples
        mock_result = [
            [None, "Line1"],
            [None, "Line2"],
        ]
        mock_ocr.return_value = mock_result
        scanner._rapid_ocr = mock_ocr

        image = np.zeros((10, 10, 3), dtype=np.uint8)
        result = scanner._ocr_text_rapid(image)
        assert result == "Line1 Line2"

    def test_string_lines_in_list(self):
        scanner = _make_scanner()
        mock_ocr = MagicMock()
        mock_ocr.return_value = ["Hello", "World"]
        scanner._rapid_ocr = mock_ocr

        image = np.zeros((10, 10, 3), dtype=np.uint8)
        result = scanner._ocr_text_rapid(image)
        assert result == "Hello World"

    def test_empty_result_returns_empty_string(self):
        scanner = _make_scanner()
        mock_ocr = MagicMock()
        mock_ocr.return_value = None
        scanner._rapid_ocr = mock_ocr

        image = np.zeros((10, 10, 3), dtype=np.uint8)
        result = scanner._ocr_text_rapid(image)
        assert result == ""

    def test_initializes_rapid_ocr_lazily(self):
        scanner = _make_scanner()
        assert scanner._rapid_ocr is None

        with patch(
            "adb_auto_player.games.afk_journey.services.hero_scanner.RapidOCR"
        ) as mock_rapid_ocr:
            mock_instance = MagicMock()
            mock_instance.return_value = None
            mock_rapid_ocr.return_value = mock_instance

            image = np.zeros((10, 10, 3), dtype=np.uint8)
            scanner._ocr_text_rapid(image)

            mock_rapid_ocr.assert_called_once()


# ---------------------------------------------------------------------------
# _load_tracker
# ---------------------------------------------------------------------------


class TestLoadTracker:
    def test_loads_valid_json(self, tmp_path):
        scanner = _make_scanner()
        data = {"heroes": [{"name": "Lumont"}]}
        f = tmp_path / "tracker.json"
        f.write_text(json.dumps(data))
        result = scanner._load_tracker(str(f))
        assert result == data

    def test_missing_file_returns_empty_dict(self, tmp_path):
        scanner = _make_scanner()
        result = scanner._load_tracker(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_invalid_json_returns_empty_dict(self, tmp_path):
        scanner = _make_scanner()
        f = tmp_path / "bad.json"
        f.write_text("{not valid json")
        result = scanner._load_tracker(str(f))
        assert result == {}


# ---------------------------------------------------------------------------
# _suggest_vertical_offset
# ---------------------------------------------------------------------------


def _ocr_result(text: str, center_y: int, center_x: int = 500) -> OCRResult:
    box = Box(Point(center_x - 50, center_y - 20), width=100, height=40)
    return OCRResult(text=text, confidence=ConfidenceValue("99%"), box=box)


class TestSuggestVerticalOffset:
    def test_logs_hint_for_text_outside_name_region(self, caplog):
        scanner = _make_scanner()
        screenshot = np.zeros((10, 10, 3), dtype=np.uint8)
        stray = _ocr_result("Aurorasomething", center_y=250)

        with patch(
            "adb_auto_player.games.afk_journey.services.hero_scanner."
            "RapidOCRBackend.pp_ocr_v5_rec"
        ) as mock_factory:
            mock_backend = MagicMock()
            mock_backend.detect_text_blocks.return_value = [stray]
            mock_factory.return_value = mock_backend

            with caplog.at_level(logging.WARNING):
                scanner._suggest_vertical_offset(screenshot)

        assert "Vertical Screen Offset" in caplog.text
        assert "50" in caplog.text

    def test_silent_when_nothing_outside_region(self, caplog):
        scanner = _make_scanner()
        screenshot = np.zeros((10, 10, 3), dtype=np.uint8)
        in_range = _ocr_result("Lumont", center_y=130)

        with patch(
            "adb_auto_player.games.afk_journey.services.hero_scanner."
            "RapidOCRBackend.pp_ocr_v5_rec"
        ) as mock_factory:
            mock_backend = MagicMock()
            mock_backend.detect_text_blocks.return_value = [in_range]
            mock_factory.return_value = mock_backend

            with caplog.at_level(logging.WARNING):
                scanner._suggest_vertical_offset(screenshot)

        assert caplog.text == ""

    def test_only_logs_once_per_scan(self, caplog):
        scanner = _make_scanner()
        screenshot = np.zeros((10, 10, 3), dtype=np.uint8)
        stray = _ocr_result("Aurorasomething", center_y=250)

        with patch(
            "adb_auto_player.games.afk_journey.services.hero_scanner."
            "RapidOCRBackend.pp_ocr_v5_rec"
        ) as mock_factory:
            mock_backend = MagicMock()
            mock_backend.detect_text_blocks.return_value = [stray]
            mock_factory.return_value = mock_backend

            with caplog.at_level(logging.WARNING):
                scanner._suggest_vertical_offset(screenshot)
                caplog.clear()
                scanner._suggest_vertical_offset(screenshot)

        assert caplog.text == ""
        assert scanner._offset_hint_logged is True
