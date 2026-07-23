"""Tests for `_GuildScanRankingsMixin._suggest_vertical_offset`.

Regression coverage for the diagnostic hint added after a report of a device
(a real Pixel phone with a `wm size` override on a mismatched aspect ratio)
where date tabs rendered outside the expected screen region and the user had
to guess the Vertical Screen Offset by trial and error.
"""

import logging
from unittest.mock import MagicMock

import numpy as np
from adb_auto_player.games.afk_journey.mixins._guild_scan_rankings import (
    _GuildScanRankingsMixin,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.ocr import OCRResult


class _Stub(_GuildScanRankingsMixin):
    """Minimal stub — only the pure-logic method under test is exercised."""


def _ocr_result(text: str, center_y: int) -> OCRResult:
    box = Box(Point(300, center_y - 20), width=100, height=40)
    return OCRResult(text=text, confidence=ConfidenceValue("99%"), box=box)


def _block(text: str, x: int, center_y: int) -> OCRResult:
    box = Box(Point(x, center_y - 20), width=100, height=40)
    return OCRResult(text=text, confidence=ConfidenceValue("99%"), box=box)


def test_suggest_vertical_offset_logs_hint_for_stray_date_text(caplog):
    bot = _Stub()
    # 50px below the bottom edge of the expected window (_Y_MAX_DATE).
    stray = _ocr_result("11/20", center_y=bot._Y_MAX_DATE + 50)
    ocr_results = [stray, _ocr_result("Guild Members", center_y=500)]

    with caplog.at_level(logging.WARNING):
        bot._suggest_vertical_offset(ocr_results)

    assert "Vertical Screen Offset" in caplog.text
    assert "50" in caplog.text


def test_suggest_vertical_offset_silent_when_nothing_date_shaped(caplog):
    bot = _Stub()
    ocr_results = [_ocr_result("Guild Members", center_y=900)]

    with caplog.at_level(logging.WARNING):
        bot._suggest_vertical_offset(ocr_results)

    assert caplog.text == ""


def test_suggest_vertical_offset_silent_when_date_text_already_in_range(caplog):
    bot = _Stub()
    in_range = _ocr_result("11/20", center_y=(bot._Y_MIN_DATE + bot._Y_MAX_DATE) // 2)

    with caplog.at_level(logging.WARNING):
        bot._suggest_vertical_offset([in_range])

    assert caplog.text == ""


def test_find_date_tabs_falls_back_to_full_screen_search(caplog):
    """A screen-specific shift (e.g. an event banner) must self-correct.

    Regression: recommending the global Vertical Screen Offset for a shift
    that only affects this one screen breaks taps everywhere else in the
    game. `_find_date_tabs` must find the row wherever it actually is before
    ever suggesting that setting.
    """
    bot = _Stub()
    below_window_y = bot._Y_MAX_DATE + 83
    row = [
        _block("11/18", x=250, center_y=below_window_y),
        _block("11/19", x=450, center_y=below_window_y),
        _block("11/20", x=650, center_y=below_window_y),
    ]
    bot.get_screenshot = MagicMock(return_value=np.zeros((1920, 1080, 3)))
    ocr_backend = MagicMock()
    ocr_backend.detect_text_blocks.return_value = row

    with caplog.at_level(logging.INFO):
        date_tabs = bot._find_date_tabs(ocr_backend)

    assert [r.text for r in date_tabs] == ["11/18", "11/19", "11/20"]
    assert "Vertical Screen Offset" not in caplog.text
    assert "found them at" in caplog.text


def test_find_date_tabs_suggests_offset_when_row_not_found_anywhere(caplog):
    """No usable date-tab row anywhere: fall back to the diagnostic hint.

    A stray date-shaped block outside the date-tab X-range (`_X_MIN_DATE_TAB`)
    isn't a usable row match, but `_suggest_vertical_offset` doesn't filter on
    X and still surfaces it — preserving the original diagnostic for a real
    device-level `wm size` mismatch.
    """
    bot = _Stub()
    bot.get_screenshot = MagicMock(return_value=np.zeros((1920, 1080, 3)))
    ocr_backend = MagicMock()
    ocr_backend.detect_text_blocks.return_value = [
        _block("11/20", x=50, center_y=bot._Y_MAX_DATE + 50),
    ]

    with caplog.at_level(logging.INFO):
        date_tabs = bot._find_date_tabs(ocr_backend)

    assert date_tabs == []
    assert "Vertical Screen Offset" in caplog.text
    assert "found them at" not in caplog.text


def test_parse_rankings_bbox_does_not_split_row_on_stray_score_label():
    """Regression: a stray label near a row's top edge split it in two.

    A duplicate 'Season' label near a row's top edge could anchor the
    row-grouping window there. The row's own rank/score blocks then fell
    outside that fixed window and were split into a second, name-less row —
    reproduced from a real Dream Realm scan frame where the pinned
    own-account row ("CTL | Maciejson", rank 211) split into
    (rank=None, name="CTL | Maciejson") and (rank="211", name=None).
    """
    bot = _Stub()
    screenshot = np.zeros((100, 100, 3), dtype=np.uint8)
    ocr_backend = MagicMock()
    ocr_backend.detect_text_blocks.return_value = [
        _block("Season", x=922, center_y=1562),
        _block("Season", x=922, center_y=1623),
        _block("CTL | MaciejsonG471", x=448, center_y=1634),
        _block("211", x=98, center_y=1656),
        _block("317B", x=913, center_y=1678),
        _block("CITADEL", x=427, center_y=1691),
    ]

    parsed_rows, _debug_rows, _ocr_results = bot._parse_rankings_bbox(
        screenshot, ocr_backend, y_min=780, is_supreme_arena=False
    )

    assert len(parsed_rows) == 1
    rank, name, score = parsed_rows[0]
    assert rank == "211"
    assert name == "CTL | Maciejson"
    assert score == "317B"
