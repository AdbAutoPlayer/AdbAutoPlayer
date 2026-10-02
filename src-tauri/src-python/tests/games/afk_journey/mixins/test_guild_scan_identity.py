"""Tests for telling apart guild members who share the same name.

Two members of guild "Yggdrasil" are both called "모험가" (same server and
district); the rankings list can't distinguish them, so the scan opens each
such row's profile panel and reads "User ID: <id>  Server: <code>".
"""

from unittest.mock import MagicMock, patch

import numpy as np
from adb_auto_player.games.afk_journey.mixins.guild_member_scan import (
    GuildMemberScanMixin,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.ocr import OCRResult

_A = {"id": 1790897106436827, "name": "모험가", "server": "H125", "userId": "111111"}
_B = {"id": 1790897118828322, "name": "모험가", "server": "H125", "userId": "222222"}
_LOKI = {"id": 1, "name": "Loki", "server": "H125", "userId": ""}

_SLEEP = "adb_auto_player.games.afk_journey.mixins._guild_scan_identity.sleep"


class _GuildScan(GuildMemberScanMixin):
    """Minimal stub — device calls are mocked per test."""

    def __init__(self):
        # Typed MagicMock handles for assertions: the overridden attributes
        # keep the method signatures in the type checker's view
        self.tap_mock = MagicMock()
        self.screenshot_mock = MagicMock(
            return_value=np.zeros((1920, 1080, 3), np.uint8)
        )
        self.tap = self.tap_mock
        self.get_screenshot = self.screenshot_mock


def _bot(players: list[dict] | None = None) -> _GuildScan:
    players = [_LOKI, _A, _B] if players is None else players
    bot = _GuildScan()
    bot._guild_members = [p["name"] for p in players]
    bot._analyze_duplicate_names(players)
    return bot


def _block(text: str, cx: int, cy: int) -> OCRResult:
    box = Box(Point(max(cx - 40, 0), max(cy - 15, 0)), 80, 30)
    return OCRResult(text=text, confidence=ConfidenceValue("90%"), box=box)


def _panel(user_id: str, server: str = "H125") -> list[OCRResult]:
    # The copy icon after the ID is often read as a stray "1".
    return [_block(f"User ID: {user_id} 1 Server: {server}", 408, 1425)]


def _row(cy: int = 1250) -> list[OCRResult]:
    return [
        _block("70", 101, cy + 22),
        _block("모험가H125", 380, cy),
        _block("Yggdrasil", 418, cy + 60),
        _block("822M", 911, cy + 45),
    ]


def _frame() -> np.ndarray:
    return np.zeros((1920, 1080, 3), np.uint8)


def _label(record: dict) -> str:
    return f"{record['name']}#{record['id']}"


class TestAnalyzeDuplicateNames:
    def test_groups_only_shared_names(self):
        bot = _bot()
        assert list(bot._duplicate_groups) == ["모험가"]
        assert bot._duplicate_group("Loki") is None

    def test_warns_when_same_server_and_no_user_id(self, caplog):
        a = {**_A, "userId": ""}
        _bot([a, _B])
        assert "userId field of the Guild Manager" in caplog.text

    def test_no_warning_when_servers_differ(self, caplog):
        a = {**_A, "userId": "", "server": "H124"}
        b = {**_B, "userId": ""}
        _bot([a, b])
        assert "userId field" not in caplog.text


class TestReadProfileIdentity:
    def test_parses_footer_with_copy_icon_noise(self):
        blocks = [
            _block("Rashoova", 368, 595),
            _block("User ID: 44942604 1 Server: G439", 408, 1425),
        ]
        assert _GuildScan._read_profile_identity(blocks) == ("44942604", "G439")

    def test_no_footer(self):
        assert _GuildScan._read_profile_identity([_block("Loki", 1, 1)]) == (
            None,
            None,
        )


class TestMatchDuplicateRecord:
    def test_by_user_id(self):
        assert _GuildScan._match_duplicate_record([_A, _B], "222222", "H125") is _B

    def test_by_server_when_user_id_missing(self):
        a = {**_A, "userId": "", "server": "H124"}
        b = {**_B, "userId": ""}
        assert _GuildScan._match_duplicate_record([a, b], "999", "H124") is a

    def test_ambiguous(self):
        a = {**_A, "userId": ""}
        b = {**_B, "userId": ""}
        assert _GuildScan._match_duplicate_record([a, b], "999", "H125") is None


class TestIdentifyDuplicateRow:
    def _identify(self, bot, result, row, panel_blocks):
        backend = MagicMock()
        backend.detect_text_blocks.return_value = panel_blocks
        with patch(_SLEEP):
            return bot._identify_duplicate_row(result, row, 780, backend, _frame())

    def test_opens_profile_reads_id_and_closes(self):
        bot = _bot()
        result = self._identify(bot, ("70", "모험가", "822M"), _row(), _panel("222222"))
        assert result == ("70", _label(_B), "822M")
        taps = [c.args[0] for c in bot.tap_mock.call_args_list]
        assert taps[0].x == bot._X_ROW_TAP
        assert taps[1] == Point(*bot._PROFILE_CLOSE)

    def test_each_row_opened_once_per_date(self):
        bot = _bot()
        for cy in (1250, 1060):  # same row, next frame after a scroll
            result = self._identify(
                bot, ("70", "모험가", "822M"), _row(cy), _panel("222222")
            )
        assert result[1] == _label(_B)
        assert bot.tap_mock.call_count == 2  # one open + one close

    def test_unique_names_are_never_opened(self):
        bot = _bot()
        result = self._identify(bot, ("1", "Loki", "6944M"), _row(), _panel("1"))
        assert result == ("1", "Loki", "6944M")
        bot.tap_mock.assert_not_called()

    def test_row_cut_off_at_list_edge_is_skipped(self):
        """A tap there could open the pinned own-player row instead."""
        bot = _bot()
        result = self._identify(
            bot, ("70", "모험가", "822M"), _row(cy=800), _panel("222222")
        )
        assert result == ("70", "모험가", "822M")
        bot.tap_mock.assert_not_called()

    def test_panel_not_opened_does_not_tap_close(self):
        """On the list, the "close" spot is the bottom navigation bar."""
        bot = _bot()
        result = self._identify(bot, ("70", "모험가", "822M"), _row(), [])
        assert result == ("70", "모험가", "822M")
        assert bot.tap_mock.call_count == 1

    def test_row_that_moved_is_not_tapped_and_retried_later(self):
        """The list still settling after the swipe: the tap could hit a neighbour."""
        bot = _bot()
        moved = _frame()
        moved[1200:1300] = 255
        bot.screenshot_mock.return_value = moved
        result = self._identify(bot, ("70", "모험가", "822M"), _row(), _panel("222222"))
        assert result == ("70", "모험가", "822M")
        bot.tap_mock.assert_not_called()
        assert ("70", "822M") not in bot._identity_cache

    def test_unknown_user_id_keeps_plain_name(self):
        bot = _bot()
        result = self._identify(bot, ("70", "모험가", "822M"), _row(), _panel("999"))
        assert result == ("70", "모험가", "822M")


class TestNamesakesSurviveCanonicalization:
    def test_both_kept_and_exported_with_roster_id(self):
        bot = _bot()
        observations: list[tuple[str | None, str | None]] = [
            ("1", "Loki"),
            ("70", _label(_A)),
            ("70", "모험가"),  # cut-off sighting of the same row
            ("90", _label(_B)),
            ("90", _label(_B)),
        ]
        observations = bot._apply_identity_labels(observations)
        canonical = bot._canonicalize_observations(observations, "Thursday")
        final = bot._correct_names_with_guild_members(canonical, bot._guild_members)
        assert final == [
            {"Date": "Thursday", "Rank": "1", "Name": "Loki"},
            {"Date": "Thursday", "Rank": "70", "Name": "모험가", "Id": _A["id"]},
            {"Date": "Thursday", "Rank": "90", "Name": "모험가", "Id": _B["id"]},
        ]

    def test_unidentified_leftover_not_exported_next_to_identified(self):
        bot = _bot()
        canonical = [
            {"Date": "Thursday", "Rank": "70", "Name": _label(_A)},
            {"Date": "Thursday", "Rank": "95", "Name": "모험가"},
        ]
        final = bot._correct_names_with_guild_members(canonical, bot._guild_members)
        assert final == [
            {"Date": "Thursday", "Rank": "70", "Name": "모험가", "Id": _A["id"]}
        ]

    def test_label_of_unknown_id_is_not_trusted(self):
        bot = _bot()
        assert bot._split_identity_label("모험가#123") is None


class TestCarryIdentityLabels:
    def test_qwen_row_gets_label_from_bbox_row_at_same_rank(self):
        bot = _bot()
        rows = [("70", "모험가", "822M"), ("1", "Loki", "6944M")]
        bbox_rows = [("70", _label(_A), "822M"), ("1", "Loki", "6944M")]
        assert bot._carry_identity_labels(rows, bbox_rows) == [
            ("70", _label(_A), "822M"),
            ("1", "Loki", "6944M"),
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Guild members list (activeness): tap on the avatar, not the row
# ─────────────────────────────────────────────────────────────────────────────


class TestActivenessNamesakes:
    def _backend(self, panel):
        bot_backend = MagicMock()
        bot_backend.detect_text_blocks.return_value = panel
        return bot_backend

    def test_avatar_tapped_left_of_and_below_the_name(self):
        bot = _bot()
        bot._rapidocr_supplement = self._backend(_panel("111111"))
        with patch(_SLEEP):
            name = bot._identify_activeness_namesake("모험가", 922, _frame())
        assert name == _label(_A)
        tap = bot.tap_mock.call_args_list[0].args[0]
        assert tap == Point(bot._X_AVATAR_TAP, 922 + bot._AVATAR_BELOW_NAME_OFFSET)

    def test_unique_member_not_tapped(self):
        bot = _bot()
        bot._rapidocr_supplement = self._backend(_panel("1"))
        assert bot._identify_activeness_namesake("Loki", 922, _frame()) == "Loki"
        bot.tap_mock.assert_not_called()

    def test_avatar_behind_sort_buttons_not_tapped(self):
        """The "Activeness / Descending" buttons cover the bottom row."""
        bot = _bot()
        bot._rapidocr_supplement = self._backend(_panel("111111"))
        assert bot._identify_activeness_namesake("모험가", 1600, _frame()) == "모험가"
        bot.tap_mock.assert_not_called()

    def test_export_restores_name_and_adds_id(self):
        bot = _bot()
        records = [
            {"Name": _label(_A), "Activeness": 1490},
            {"Name": _label(_B), "Activeness": 900},
            {"Name": "모험가", "Activeness": 10},  # unidentified sighting
            {"Name": "Loki", "Activeness": 1780},
        ]
        assert bot._export_activeness_identities(records) == [
            {"Name": "모험가", "Activeness": 1490, "Id": _A["id"]},
            {"Name": "모험가", "Activeness": 900, "Id": _B["id"]},
            {"Name": "Loki", "Activeness": 1780},
        ]

    def test_identity_labels_survive_roster_correction(self):
        bot = _bot()
        records = [{"Name": _label(_B), "Activeness": 900}]
        assert (
            bot._filter_and_correct_activeness_records(records, bot._guild_members)
            == records
        )

    def test_chest_value_not_given_to_namesakes(self):
        """The chest ranking opens no profile: the value goes in by hand."""
        bot = _bot()
        bot._navigate_to_guild_hall = MagicMock(return_value=True)
        bot._scan_guild_chest_contributions = MagicMock(
            return_value={"모험가": 120, "Loki": 175}
        )
        bot._navigate_to_guild_members_screen = MagicMock(return_value=True)
        bot._collect_activeness_scroll_data = MagicMock(
            return_value=[
                {"Name": _label(_A), "Activeness": 1490},
                {"Name": "Loki", "Activeness": 1780},
            ]
        )
        bot._save_guild_activeness_to_json = MagicMock()
        with patch(
            "adb_auto_player.games.afk_journey.mixins._guild_scan_activeness."
            "RapidOCRBackend"
        ):
            bot._scan_guild_activeness(MagicMock(), bot._guild_members)
        saved = bot._save_guild_activeness_to_json.call_args.args[0]
        assert saved == [
            {"Name": "모험가", "Activeness": 1490, "Id": _A["id"]},
            {"Name": "Loki", "Activeness": 1780, "ChestContribution": 175},
        ]


class TestActivenessScriptRecovery:
    def test_orphaned_value_gets_name_from_line_above(self):
        """The CH model found no name block at all for this Korean member."""
        bot = _bot([_LOKI, {"id": 5, "name": "이른봄날", "server": "H125"}])
        bot._activeness_qwen = None
        bot._read_script_text_at = MagicMock(return_value="이른봄날")
        located: list = []
        value = _block("1400", 815, 1018)
        bot._recover_activeness_script_names(_frame(), [value], set(), located)
        assert located == [
            ("이른봄날", "1400", 1018 - bot._ACTIVENESS_VALUE_BELOW_NAME)
        ]

    def test_misread_name_replaced(self):
        bot = _bot([_LOKI, {"id": 5, "name": "이른봄날", "server": "H125"}])
        bot._activeness_qwen = None
        bot._read_script_text_at = MagicMock(return_value="이른봄날")
        located = [("CTL0✨", "1400", 922)]
        bot._recover_activeness_script_names(_frame(), [], set(), located)
        assert located == [("이른봄날", "1400", 922)]

    def test_nothing_read_without_korean_or_cyrillic_members(self):
        bot = _bot([_LOKI])
        bot._read_script_text_at = MagicMock()
        located = [("CTL0✨", "1400", 922)]
        bot._recover_activeness_script_names(_frame(), [], set(), located)
        bot._read_script_text_at.assert_not_called()
