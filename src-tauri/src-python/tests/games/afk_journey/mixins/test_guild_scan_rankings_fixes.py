# ruff: noqa: RUF001  -- real Cyrillic member names are the test data
"""Regression tests for the Dream Realm / AFK Stage rankings scan fixes.

Built from a user's debug run (guild "Yggdrasil", RapidOCR only, no Qwen):
- the player's own row pinned over the list merged into the row beneath it
- Korean names never read (CH model has no Hangul), and every pseudo-CJK
  misread force-matched to the first Korean roster member
- Cyrillic names read as Latin lookalikes ("CKnTaJe") and discarded
- "Toki" dropped as a fuzzy duplicate of "Loki" (ratio exactly 0.75)
"""

from unittest.mock import MagicMock, patch

import numpy as np
from adb_auto_player.games.afk_journey.mixins._guild_scan_rankings import (
    _CYRILLIC_RE,
    _HANGUL_RE,
)
from adb_auto_player.games.afk_journey.mixins._guild_scan_setup import (
    _GuildScanSetupMixin,
)
from adb_auto_player.games.afk_journey.mixins.guild_member_scan import (
    GuildMemberScanMixin,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.ocr import OCRResult

_ROSTER = [
    "Loki",
    "Toki",
    "Tenet",
    "Zoltraak",
    "라이키키",
    "또깅",
    "도로롱",
    "메이",
    "菜菜大王",
    "はーちゃん",
    "Liano",
    "Скиталец",
    "Диас",
]


class _GuildScan(GuildMemberScanMixin):
    """Minimal stub — only pure-logic methods are exercised."""


def _bot(roster: list[str] | None = None) -> _GuildScan:
    bot = _GuildScan()
    bot._guild_members = list(_ROSTER if roster is None else roster)
    return bot


def _block(text: str, cx: int, cy: int) -> OCRResult:
    box = Box(Point(max(cx - 40, 0), max(cy - 15, 0)), 80, 30)
    return OCRResult(text=text, confidence=ConfidenceValue("90%"), box=box)


def _screenshot() -> np.ndarray:
    return np.zeros((1920, 1080, 3), dtype=np.uint8)


def _pinned_loki() -> list[OCRResult]:
    return [
        _block("LokiH125", 387, 885),
        _block("Season", 922, 874),
        _block("6944M", 914, 929),
        _block("Yggdrasil", 421, 945),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Scroll limit
# ─────────────────────────────────────────────────────────────────────────────


def test_max_scrolls_covers_a_full_guild_list():
    """25 scrolls stopped at rank ~115 with ~30 members still unscanned."""
    assert _GuildScanSetupMixin._MAX_SCROLLS >= 60


# ─────────────────────────────────────────────────────────────────────────────
# Pinned own-player row
# ─────────────────────────────────────────────────────────────────────────────


class TestPinnedRowFilter:
    def _parse(self, bot, blocks, first: bool):
        if first:
            bot._prev_ranking_blocks = []
        backend = MagicMock()
        backend.detect_text_blocks.return_value = blocks
        rows, _, _ = bot._parse_rankings_bbox(
            _screenshot(), backend, 820 if first else 780, False
        )
        return rows

    def test_pinned_row_does_not_merge_into_row_below(self):
        """Frame 10: pinned Loki merged with the cut-off rank-26 row."""
        bot = _bot([])
        frame0 = [
            *_pinned_loki(),
            _block("2", 100, 1089),
            _block("TenetH125", 400, 1071),
            _block("Season", 923, 1060),
            _block("5363M", 912, 1115),
        ]
        self._parse(bot, frame0, first=True)

        frame1 = [
            *_pinned_loki(),
            _block("26", 100, 1010),
            _block("1352M", 911, 1010),
            _block("Yggdrasil", 418, 1025),
            _block("35", 101, 1545),
            _block("TokiH125", 390, 1522),
            _block("Season", 922, 1512),
            _block("1201M", 912, 1567),
        ]
        rows = self._parse(bot, frame1, first=False)

        assert all(name != "Loki" for _, name, _ in rows)
        assert ("35", "Toki", "1201M") in rows

    def test_first_frame_keeps_rows_at_pinned_position(self):
        """Frame 0 has no previous frame: the natural rank-1 row must stay."""
        bot = _bot([])
        rows = self._parse(bot, [_block("1", 100, 905), *_pinned_loki()], first=True)
        assert rows[0][1] == "Loki"

    def test_first_frame_of_next_date_resets_previous_blocks(self):
        """A new date tab starts over: its first frame must not be filtered."""
        bot = _bot([])
        bot._ocr_debug = None
        blocks = [_block("1", 100, 905), *_pinned_loki()]
        backend = MagicMock()
        backend.detect_text_blocks.return_value = blocks
        bot._parse_rankings_rows(_screenshot(), backend, is_first_frame=True)
        rows = bot._parse_rankings_rows(_screenshot(), backend, is_first_frame=True)
        assert rows[0][1] == "Loki"


# ─────────────────────────────────────────────────────────────────────────────
# Korean / Cyrillic name recovery
# ─────────────────────────────────────────────────────────────────────────────


def _engines(bot, korean="", cyrillic=""):
    """Install mocked per-script recognizers; str or list (side_effect)."""
    engines = {}
    for label, reads in (("korean", korean), ("cyrillic", cyrillic)):
        engine = MagicMock()
        if isinstance(reads, list):
            engine.recognize_line.side_effect = reads
        else:
            engine.recognize_line.return_value = reads
        engines[label] = engine
    bot._script_ocr = engines
    return engines


class TestExtractScriptName:
    def test_hangul_strips_badge_and_avatar_noise(self):
        assert _GuildScan._extract_script_name("또깅H25", _HANGUL_RE) == "또깅"
        assert _GuildScan._extract_script_name("도로롱25", _HANGUL_RE) == "도로롱"
        assert _GuildScan._extract_script_name("AN무이미H25", _HANGUL_RE) == "무이미"
        assert (
            _GuildScan._extract_script_name("김재혁잉아H125", _HANGUL_RE)
            == "김재혁잉아"
        )

    def test_cyrillic_strips_badge_variants(self):
        """The badge reads as "H125", "н125" (Cyrillic en), "(125" or a digit."""
        extract = _GuildScan._extract_script_name
        assert extract("ВиллиH125", _CYRILLIC_RE) == "Вилли"
        assert extract("Аянами Рейн125", _CYRILLIC_RE) == "Аянами Рей"
        assert extract("Скиталец(25", _CYRILLIC_RE) == "Скиталец"
        assert extract("Диас2", _CYRILLIC_RE) == "Диас"
        assert extract("Поганец", _CYRILLIC_RE) == "Поганец"

    def test_other_script_returns_none(self):
        assert _GuildScan._extract_script_name("CKMTaIelH5", _HANGUL_RE) is None
        assert _GuildScan._extract_script_name("NubladoH125", _CYRILLIC_RE) is None
        assert _GuildScan._extract_script_name("", _HANGUL_RE) is None


class TestNeedsNameRecovery:
    def _needs(self, name, roster=None):
        bot = _bot(roster)
        return bot._needs_name_recovery(name, bot._roster_recovery_scripts())

    def test_missing_name(self):
        assert self._needs(None)

    def test_pseudo_cjk_misread(self):
        assert self._needs("丘号")
        assert self._needs("エ刀")

    def test_symbol_noise(self):
        assert self._needs("STH|∈∈|02")

    def test_latin_lookalike_of_cyrillic(self):
        assert self._needs("CKnTaJe")

    def test_weak_match_to_another_member(self):
        """A Cyrillic misread scoring 0.67 vs "Liano" is not trustworthy."""
        assert self._needs("Lnac")

    def test_roster_names_are_left_alone(self):
        for name in ("Toki", "菜菜大王", "はーちゃん", "또깅", "Скиталец"):
            assert not self._needs(name)

    def test_near_miss_of_other_member_is_left_alone(self):
        assert not self._needs("Zoltrak")
        assert not self._needs("3Garodis", [*_ROSTER, "Garodis"])


class TestRecoverScriptName:
    def _row(self):
        return [
            _block("16", 101, 1512),
            _block("エ刀H125", 377, 1490),
            _block("Yggdrasil", 418, 1550),
            _block("Season", 922, 1480),
            _block("1468M", 911, 1535),
        ]

    def _recover(self, bot, result, row=None):
        return bot._recover_script_name(
            result, row or self._row(), _screenshot(), MagicMock()
        )

    def test_pseudo_cjk_replaced_with_korean_read(self):
        bot = _bot()
        engines = _engines(bot, korean="또깅H25")
        result = self._recover(bot, ("16", "エ刀", "1468M"))
        assert result == ("16", "또깅", "1468M")
        engines["cyrillic"].recognize_line.assert_not_called()

    def test_latin_lookalike_replaced_with_cyrillic_read(self):
        bot = _bot()
        _engines(bot, korean="CKMTaIelH5", cyrillic="Скиталец(25")
        result = self._recover(bot, ("45", "CKnTaJe", "1075M"))
        assert result == ("45", "Скиталец", "1075M")

    def test_crop_is_centered_on_name_line_above_rank(self):
        bot = _bot()
        engines = _engines(bot, korean="또깅H25")
        self._recover(bot, ("16", "エ刀", "1468M"))
        crop = engines["korean"].recognize_line.call_args_list[0].args[0]
        assert crop.shape[0] == 2 * bot._NAME_CROP_HALF_HEIGHTS[0]
        assert crop.shape[1] == bot._X_SCORE_BOUNDARY - bot._X_NAME_CROP_MIN

    def test_longest_read_wins(self):
        """A tight crop read "리" for "유리"; the taller crop got it whole."""
        bot = _bot([*_ROSTER, "유리"])
        _engines(bot, korean=["리H5", "유리25"])
        result = self._recover(bot, ("60", None, "890M"))
        assert result[1] == "유리"

    def test_missing_rank_is_reread_from_badge(self):
        """Phase 1 rank 9: neither the "9" badge nor "또깅" was detected."""
        bot = _bot()
        _engines(bot, korean="또깅")
        row = [
            _block("Yggdrasil", 419, 1283),
            _block("Phase Progress", 945, 1212),
            _block("443", 947, 1265),
        ]
        with patch.object(bot, "_extract_rank_from_crop", return_value="9") as crop:
            result = self._recover(bot, (None, None, "443"), row)
        assert result == ("9", "또깅", "443")
        crop.assert_called_once()

    def test_unrecoverable_pseudo_cjk_is_dropped_not_force_matched(self):
        """Used to become 라이키키 (first Korean member) via the 0.7 floor."""
        bot = _bot()
        _engines(bot)
        result = self._recover(bot, ("16", "エ刀", "1468M"))
        assert result == ("16", None, "1468M")

    def test_unrecoverable_latin_noise_is_kept(self):
        bot = _bot()
        _engines(bot, korean="CKMTaIelH5", cyrillic="CKMTaIelH5")
        result = self._recover(bot, ("45", "CKnTaJe", "1075M"))
        assert result == ("45", "CKnTaJe", "1075M")

    def test_skipped_when_roster_has_no_korean_or_cyrillic_members(self):
        bot = _bot(["Loki", "Toki"])
        engines = _engines(bot)
        result = self._recover(bot, ("16", None, "1468M"))
        assert result == ("16", None, "1468M")
        engines["korean"].recognize_line.assert_not_called()
        engines["cyrillic"].recognize_line.assert_not_called()

    def test_only_scripts_present_in_roster_are_tried(self):
        bot = _bot(["Loki", "Скиталец"])
        engines = _engines(bot, cyrillic="Скиталец")
        result = self._recover(bot, ("45", "CKnTaJe", "1075M"))
        assert result[1] == "Скиталец"
        engines["korean"].recognize_line.assert_not_called()

    def test_skipped_for_correctly_read_names(self):
        bot = _bot()
        engines = _engines(bot)
        self._recover(bot, ("35", "Toki", "1201M"))
        engines["korean"].recognize_line.assert_not_called()
        engines["cyrillic"].recognize_line.assert_not_called()


class TestKoreanMemberMatchOnJamo:
    def test_one_letter_slip_picks_the_right_member(self):
        """Per syllable "또강" ties 0.5 with both and the first member won."""
        bot = _bot(["강또", "또깅"])
        corrected = bot._correct_names_with_guild_members(
            [{"Date": "Thursday", "Rank": "16", "Name": "또강"}],
            bot._guild_members,
        )
        assert corrected[0]["Name"] == "또깅"


# ─────────────────────────────────────────────────────────────────────────────
# Toki vs Loki
# ─────────────────────────────────────────────────────────────────────────────


class TestDistinctRosterMembersNotDeduped:
    def test_toki_kept_alongside_loki(self):
        bot = _bot()
        observations: list[tuple[str | None, str | None]] = [("1", "Loki")] * 25 + [
            ("35", "Toki"),
            ("35", "Toki"),
        ]
        results = bot._canonicalize_observations(observations, "Thursday")
        assert {"Date": "Thursday", "Rank": "35", "Name": "Toki"} in results
        assert {"Date": "Thursday", "Rank": "1", "Name": "Loki"} in results

    def test_ocr_variant_of_member_still_deduped(self):
        """A non-roster variant like "Lokii" is still Loki's misread."""
        bot = _bot()
        observations: list[tuple[str | None, str | None]] = [
            ("1", "Loki"),
            ("1", "Loki"),
            ("40", "Lokii"),
        ]
        results = bot._canonicalize_observations(observations, "Thursday")
        assert [r["Name"] for r in results] == ["Loki"]

    def test_without_roster_behaviour_is_unchanged(self):
        bot = _bot([])
        observations: list[tuple[str | None, str | None]] = [
            ("1", "Loki"),
            ("1", "Loki"),
            ("35", "Toki"),
        ]
        results = bot._canonicalize_observations(observations, "Thursday")
        assert [r["Name"] for r in results] == ["Loki"]
