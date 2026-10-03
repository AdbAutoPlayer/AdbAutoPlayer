"""Regression tests from a full Guild Manager Scan run (guild "Yggdrasil").

RapidOCR only. Each case is taken from the user's debug frames:
- Supreme Arena: guild line taken as the name, no Korean/Cyrillic recovery,
  gold rank-1 badge unread, rank digits merged into the name block
- AFK Stages: "8" read "80", "171" read "7" at the bottom edge, a stray "6"
  picked over "Penguasa Elemen", "오望外" (half-misread "모험가")
- Activeness / chest: role labels stealing values, a status icon read as a
  CJK glyph ("CHzGOD金"), "4115" for 115, Toki merged into Loki, non-members
  added from the chest list
"""

from unittest.mock import MagicMock, patch

import numpy as np
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
    "Zerelior",
    "CHzGOD",
    "Penguasa Elemen",
    "라이키키",
    "또깅",
    "모험가",
    "Диас",
]


class _GuildScan(GuildMemberScanMixin):
    """Minimal stub — only pure-logic methods are exercised."""


def _bot(roster: list[str] | None = None) -> _GuildScan:
    bot = _GuildScan()
    bot._guild_members = list(_ROSTER if roster is None else roster)
    bot._ocr_debug = None
    return bot


def _block(text: str, cx: int, cy: int, width: int = 80) -> OCRResult:
    box = Box(Point(max(cx - width // 2, 0), max(cy - 15, 0)), width, 30)
    return OCRResult(text=text, confidence=ConfidenceValue("90%"), box=box)


def _frame() -> np.ndarray:
    return np.zeros((1920, 1080, 3), np.uint8)


# ─────────────────────────────────────────────────────────────────────────────
# Frame-wide rank consistency
# ─────────────────────────────────────────────────────────────────────────────


class TestFixFrameRanks:
    def test_truncated_badge_at_bottom_edge_dropped(self):
        """Badge 171 cut off at the bottom edge, read as 7 after 159, 165."""
        rows = [
            ("149", "Ерион", "x"),
            ("159", "VerinK", "x"),
            ("165", "Kazemy", "x"),
            ("7", "Toki", None),
        ]
        fixed = _GuildScan._fix_frame_ranks(rows)
        assert fixed[-1] == (None, "Toki", None)
        assert [r[0] for r in fixed[:3]] == ["149", "159", "165"]

    def test_extra_digit_dropped_in_favour_of_smaller_run(self):
        """Badge 8 read as 80 between 7 and 9: dropped, then re-inferred as 8."""
        rows = [("7", "Liano", "x"), ("80", "또깅", "x"), ("9", "Labouboule", "x")]
        fixed = _GuildScan._fix_frame_ranks(rows)
        assert [r[0] for r in fixed] == ["7", "8", "9"]

    def test_missing_rank_between_p_and_p_plus_2(self):
        rows = [("5", "a", "x"), (None, "b", "x"), ("7", "c", "x")]
        assert _GuildScan._fix_frame_ranks(rows)[1][0] == "6"

    def test_gold_podium_badge_above_rank_2(self):
        rows = [(None, "Tenet", None), ("2", "Loki", None), ("3", "Zoltraak", None)]
        assert _GuildScan._fix_frame_ranks(rows)[0][0] == "1"

    def test_ambiguous_gap_left_unranked(self):
        rows = [("5", "a", "x"), (None, "b", "x"), ("9", "c", "x")]
        assert _GuildScan._fix_frame_ranks(rows)[1][0] is None


# ─────────────────────────────────────────────────────────────────────────────
# Single-row parsing
# ─────────────────────────────────────────────────────────────────────────────


class TestParseSingleRow:
    def test_supreme_arena_guild_line_not_taken_as_name(self):
        """No score column: an undetected Korean name left only "Yggdrasil"."""
        row = [_block("68", 103, 1292), _block("Yggdrasil", 418, 1330)]
        rank, name, _ = _bot()._parse_single_row(row, _frame(), MagicMock())
        assert (rank, name) == ("68", None)

    def test_stray_short_block_not_picked_over_name(self):
        row = [
            _block("102", 100, 1245),
            _block("6", 269, 1194, width=20),
            _block("Penguasa Elemen", 428, 1222, width=240),
            _block("Yggdrasil", 419, 1282),
            _block("307", 947, 1265),
        ]
        _, name, _ = _bot()._parse_single_row(row, _frame(), MagicMock())
        assert name == "Penguasa Elemen"

    def test_rank_digits_merged_into_name_block_stripped(self):
        row = [
            _block("414Inacu125", 270, 1435, width=260),
            _block("Yggdrasil", 418, 1484),
        ]
        backend = MagicMock()
        backend.detect_text_blocks.return_value = [_block("414", 50, 50)]
        _, name, _ = _bot()._parse_single_row(row, _frame(), backend)
        assert name == "Inac"


class TestNameRecoveryTriggers:
    def test_hangul_mixed_with_pseudo_cjk_is_recovered(self):
        bot = _bot()
        assert bot._needs_name_recovery("오望外", bot._roster_recovery_scripts())

    def test_supreme_arena_name_line_anchored_on_name_block(self):
        """No rank badge, no score: anchor the crop on the name block."""
        bot = _bot()
        bot._read_script_text_at = MagicMock(return_value="또깅")
        row = [_block("コH125", 377, 1062), _block("Yggdrasil", 419, 1123)]
        script = bot._roster_recovery_scripts()[0]
        assert bot._read_script_name_line(row, _frame(), script) == "또깅"
        assert bot._read_script_text_at.call_args.args[1] == 1062


class TestStatusIconNotKoreanMisread:
    def test_latin_name_with_cjk_glyph_matches_itself(self):
        bot = _bot()
        assert bot._correct_single_name("CHzGOD金", bot._guild_members) == "CHzGOD"

    def test_misread_japanese_member_not_forced_onto_korean(self):
        """Long-vowel mark read as kanji "一" plus an icon read as "Φ"."""
        bot = _bot([*_ROSTER, "はーちゃん"])
        assert (
            bot._correct_single_name("は一ちゃんΦ", bot._guild_members) == "はーちゃん"
        )

    def test_pseudo_cjk_korean_misread_still_goes_korean(self):
        bot = _bot([*_ROSTER, "はーちゃん"])
        assert bot._correct_single_name("丘号", bot._guild_members) in {
            "라이키키",
            "또깅",
            "모험가",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Activeness pairing
# ─────────────────────────────────────────────────────────────────────────────


class TestActivenessPairing:
    def _parse(self, blocks, roster=None):
        bot = _bot(roster or ["Zerelior", "Sakaka", "Loki"])
        backend = MagicMock()
        backend.detect_text_blocks.return_value = blocks
        return bot._parse_activeness_rows(_frame(), backend)

    def test_role_label_above_name_does_not_steal_value(self):
        """Role label Vice-/Leader (y 659/692) sits right above Zerelior (718)."""
        pairs = self._parse(
            [
                _block("Vice-", 147, 659),
                _block("Friends", 307, 675),
                _block("Leader", 148, 692),
                _block("Zerelior", 378, 718),
                _block("1460", 815, 812),
            ]
        )
        assert ("Zerelior", "1460") in pairs
        assert all(name not in {"Leader", "Vice-"} for name, _ in pairs)

    def test_value_paired_with_name_one_line_above(self):
        pairs = self._parse(
            [
                _block("Guildmate", 124, 1173),
                _block("Sakaka", 348, 1216),
                _block("1430", 815, 1310),
            ]
        )
        assert ("Sakaka", "1430") in pairs


# ─────────────────────────────────────────────────────────────────────────────
# Chest contribution
# ─────────────────────────────────────────────────────────────────────────────


class TestChestParsing:
    def test_arrow_icon_read_as_leading_4(self):
        bot = _bot()
        assert bot._chest_value("4115") == 115
        assert bot._chest_value("￥98") == 98
        assert bot._chest_value("Chest") is None

    def test_role_tag_below_value_does_not_steal_it(self):
        bot = _bot(["Zoltraak", "Zerelior"])
        backend = MagicMock()
        backend.detect_text_blocks.return_value = [
            _block("Zoltraak", 403, 1015, width=160),
            _block("115", 914, 1060),
            _block("Elder", 398, 1073),
            _block("Zerelior", 400, 1194, width=160),
            _block("4115", 914, 1239),
            _block("Vice-", 425, 1240),
            _block("Leader", 424, 1262),
        ]
        pairs = bot._parse_chest_contribution_rows(_frame(), backend)
        assert pairs == [("Zoltraak", 115), ("Zerelior", 115)]

    def test_toki_not_merged_into_loki(self):
        bot = _bot()
        bot._save_debug_screenshot = MagicMock()
        bot.swipe_up = MagicMock()
        bot.get_screenshot = MagicMock(return_value=_frame())
        frames = [[("Loki", 117)], [("Toki", 77)]] + [[]] * 10
        with (
            patch.object(bot, "_parse_chest_contribution_rows", side_effect=frames),
            patch(
                "adb_auto_player.games.afk_journey.mixins._guild_scan_activeness.sleep"
            ),
        ):
            contributions = bot._collect_chest_contribution_scroll(MagicMock())
        assert contributions == {"Loki": 117, "Toki": 77}

    def test_chest_only_entries_must_be_members(self):
        bot = _bot(["Loki", "Tenet"])
        bot._analyze_duplicate_names([])
        bot._navigate_to_guild_hall = MagicMock(return_value=True)
        bot._scan_guild_chest_contributions = MagicMock(
            return_value={"Loki": 117, "Tenet": 116, "Co-leader": 116, "||": 107}
        )
        bot._navigate_to_guild_members_screen = MagicMock(return_value=True)
        bot._collect_activeness_scroll_data = MagicMock(
            return_value=[{"Name": "Loki", "Activeness": 1670}]
        )
        bot._save_guild_activeness_to_json = MagicMock()
        with patch(
            "adb_auto_player.games.afk_journey.mixins._guild_scan_activeness."
            "RapidOCRBackend"
        ):
            bot._scan_guild_activeness(MagicMock(), bot._guild_members)
        saved = bot._save_guild_activeness_to_json.call_args.args[0]
        assert [r["Name"] for r in saved] == ["Loki", "Tenet"]
