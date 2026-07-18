"""Unit tests for GuildMemberScanMixin logic.

Covers the pure-data methods (no device/screenshot needed):
- _canonicalize_observations: ranking deduplication and Cyrillic handling
- _apply_bbox_rank_corrections: SA podium filter + rank deduplication
- llm_y_min logic in _parse_rankings_rows: correct crop per frame type
- _torch_metadata: prefers CUDA dist-info over CPU-only when both present
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
from adb_auto_player.games.afk_journey.mixins._guild_scan_setup import (
    _GuildScanSetupMixin,
)
from adb_auto_player.games.afk_journey.mixins.guild_member_scan import (
    GuildMemberScanMixin,
)
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.ocr import OCRResult
from adb_auto_player.ocr.qwen2vl_backend import QwenVLOCRBackend


class _GuildScan(GuildMemberScanMixin):
    """Minimal stub — only pure-logic methods are exercised."""


# ─────────────────────────────────────────────────────────────────────────────
# _canonicalize_observations
# ─────────────────────────────────────────────────────────────────────────────


class TestCanonicalizeObservations:
    def _bot(self):
        return _GuildScan()

    def test_ranked_observation_wins_over_null_supplements(self):
        """Sebv=7 from Qwen frame 0 must not be overridden by 6x null-rank votes."""
        bot = self._bot()
        observations = [
            ("7", "Sebv"),
            (None, "Sebv"),
            (None, "Sebv"),
            (None, "Sebv"),
            (None, "Sebv"),
            (None, "Sebv"),
            (None, "Sebv"),
        ]
        results = bot._canonicalize_observations(observations, "Wednesday")
        sebv = next((r for r in results if r["Name"] == "Sebv"), None)
        assert sebv is not None
        assert sebv["Rank"] == "7"

    def test_cyrillic_name_with_rank_included(self):
        """ОпасныйПоцык at rank 29 must appear in output."""
        bot = self._bot()
        observations = [("29", "ОпасныйПоцык"), ("29", "ОпасныйПоцык")]
        results = bot._canonicalize_observations(observations, "Tuesday")
        entry = next((r for r in results if "Поцык" in r["Name"]), None)
        assert entry is not None
        assert entry["Rank"] == "29"

    def test_ranked_beats_null_rank_for_same_player(self):
        """When a player has both ranked and null observations, rank wins."""
        bot = self._bot()
        observations = [
            ("29", "ОпасныйПоцык"),
            (None, "ОпасныйПоцык"),
            (None, "ОпасныйПоцык"),
        ]
        results = bot._canonicalize_observations(observations, "Tuesday")
        entry = next((r for r in results if "Поцык" in r["Name"]), None)
        assert entry is not None
        assert entry["Rank"] == "29"

    def test_unranked_included_when_at_threshold(self):
        """Unranked player with exactly _MIN_UNRANKED_OBSERVATIONS (2) is included."""
        bot = self._bot()
        min_obs = bot._MIN_UNRANKED_OBSERVATIONS
        observations = [(None, "GhostPlayer")] * min_obs
        results = bot._canonicalize_observations(observations, "Monday")
        entry = next((r for r in results if r["Name"] == "GhostPlayer"), None)
        assert entry is not None
        assert entry["Rank"] == ""

    def test_unranked_excluded_below_threshold(self):
        """Unranked player with fewer than _MIN_UNRANKED_OBSERVATIONS is dropped."""
        bot = self._bot()
        min_obs = bot._MIN_UNRANKED_OBSERVATIONS
        observations = [(None, "GhostPlayer")] * (min_obs - 1)
        results = bot._canonicalize_observations(observations, "Monday")
        assert not any(r["Name"] == "GhostPlayer" for r in results)

    def test_results_sorted_numerically_unranked_last(self):
        """Ranked entries are sorted numerically; unranked entries appear last."""
        bot = self._bot()
        observations = [
            ("50", "Charlie"),
            ("1", "Alice"),
            ("10", "Bob"),
            (None, "Delta"),
            (None, "Delta"),
        ]
        results = bot._canonicalize_observations(observations, "Monday")
        ranks = [r["Rank"] for r in results]
        assert ranks == ["1", "10", "50", ""]

    def test_hallucination_at_lower_rank_dropped(self):
        """When a player appears more often at rank X, rank Y is a hallucination."""
        bot = self._bot()
        # Aurion seen 1x at rank 1 (hallucination) and 5x at rank 91 (correct)
        observations = [("1", "Aurion")] + [("91", "Aurion")] * 5
        results = bot._canonicalize_observations(observations, "Monday")
        aurion = next((r for r in results if r["Name"] == "Aurion"), None)
        assert aurion is not None
        assert aurion["Rank"] == "91"

    def test_truncated_rank_tie_resolved_to_longer_rank(self):
        """Regression: "288" misread as "28" in some frames must not win a tie.

        Aroshard observed 5x at rank "288" and 5x at rank "28" (OCR badge
        noise dropped the trailing digit). An exact 5-5 tie previously fell
        back to the smaller rank number ("28", wrong) and then silently
        dropped rank "288" entirely as an already-claimed duplicate.
        """
        bot = self._bot()
        observations = [("288", "Aroshard")] * 5 + [("28", "Aroshard")] * 5
        results = bot._canonicalize_observations(observations, "Thursday")
        aroshard = [r for r in results if r["Name"] == "Aroshard"]
        assert len(aroshard) == 1
        assert aroshard[0]["Rank"] == "288"

    def test_truncated_rank_merge_ignores_unrelated_names(self):
        """A rank-prefix relationship between two different players must not merge."""
        bot = self._bot()
        observations = [("28", "Sacrifar")] * 3 + [("288", "Aroshard")] * 3
        results = bot._canonicalize_observations(observations, "Thursday")
        ranks_by_name = {r["Name"]: r["Rank"] for r in results}
        assert ranks_by_name["Sacrifar"] == "28"
        assert ranks_by_name["Aroshard"] == "288"


# ─────────────────────────────────────────────────────────────────────────────
# _apply_bbox_rank_corrections
# ─────────────────────────────────────────────────────────────────────────────


class TestApplyBboxRankCorrections:
    def _bot(self):
        return _GuildScan()

    def test_sa_non_first_filters_podium_hallucinations(self):
        """SA non-first: Qwen rows not confirmed by bbox rank_set are removed."""
        bot = self._bot()
        rows = [
            ("1", "Aurion", None),  # hallucination from podium badge
            ("2", "BlackFriday", None),  # hallucination from podium badge
            ("8", "Persephone", None),  # real entry confirmed by bbox
        ]
        bbox_rows = [("8", "Persephone", None)]
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=True, is_first_frame=False
        )
        names = [r[1] for r in result]
        assert "Aurion" not in names
        assert "BlackFriday" not in names
        assert "Persephone" in names

    def test_sa_first_no_filter_applied(self):
        """SA first frame: no bbox_rank_set filter — all rows pass through."""
        bot = self._bot()
        rows = [("1", "Aurion", None), ("7", "Sebv", None)]
        bbox_rows = [("1", "Aurion", None)]  # only Aurion in bbox
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=True, is_first_frame=True
        )
        names = [r[1] for r in result]
        assert "Aurion" in names
        assert "Sebv" in names  # Sebv passes even though not in bbox

    def test_rank_correction_via_name_lookup(self):
        """Qwen assigns wrong rank to a player that bbox correctly identified."""
        bot = self._bot()
        rows = [("5", "Sebv", None)]  # Qwen says rank 5
        bbox_rows = [("7", "Sebv", None)]  # bbox says rank 7
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=False, is_first_frame=False
        )
        assert result[0][0] == "7"
        assert result[0][1] == "Sebv"

    def test_rank_correction_ignores_pipe_spacing_differences(self):
        """Qwen and bbox spell the same name with different pipe spacing.

        Regression test: Qwen read Boki's whole row garbled as rank=5 (with
        his real rank 127 leaking into the score field), while bbox correctly
        found him at rank 127 as "CTL|Boki" (no spaces). Qwen's own spelling
        was "CTL | Boki" (with spaces), so an exact-string lookup in
        name_rank missed the match and the bad rank slipped through.
        """
        bot = self._bot()
        rows = [("5", "CTL | Boki", "127")]
        bbox_rows = [("127", "CTL|Boki", "3062B")]
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=False, is_first_frame=False
        )
        assert result[0][0] == "127"
        assert result[0][1] == "CTL | Boki"

    def test_rank_deduplication_prefers_bbox_confirmed_name(self):
        """When two players share a rank, bbox-confirmed name replaces the first."""
        bot = self._bot()
        rows = [
            ("5", "Night-", None),  # first occurrence — bbox-confirmed
            ("5", "Sebv", None),  # duplicate rank, not bbox-confirmed
        ]
        bbox_rows = [("5", "Night-", None)]
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=True, is_first_frame=True
        )
        rank5 = [r for r in result if r[0] == "5"]
        assert len(rank5) == 1
        assert rank5[0][1] == "Night-"

    def test_dr_non_first_empty_bbox_no_filter(self):
        """DR non-first with empty bbox: rank_set is empty so filter is skipped."""
        bot = self._bot()
        rows = [
            ("24", "ОпасныйПоцык", None),
            ("32", "Aroshard", None),
        ]
        result = bot._apply_bbox_rank_corrections(
            rows, [], is_supreme_arena=False, is_first_frame=False
        )
        assert len(result) == 2

    def test_dr_non_first_with_bbox_filters_unconfirmed_rank(self):
        """DR non-first with bbox data: unconfirmed rank (hallucination) is removed."""
        bot = self._bot()
        rows = [
            ("24", "ОпасныйПоцык", None),  # rank 24 not in bbox — hallucination
            ("32", "Aroshard", None),  # rank 32 confirmed by bbox
        ]
        bbox_rows = [("29", "garbled", None), ("32", "Aroshard", None)]
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=False, is_first_frame=False
        )
        ranks = [r[0] for r in result]
        assert "24" not in ranks
        assert "32" in ranks

    def test_rank_shift_correction_via_empty_ranks(self):
        """Off-by-one rank shift corrected using bbox empty_ranks heuristic."""
        bot = self._bot()
        # Qwen says rank 10, but bbox sees rank 11 empty (rank 10 not in bbox)
        rows = [("10", "PlayerA", None)]
        bbox_rows = [("11", "", None)]  # rank 11 seen as empty in bbox
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=False, is_first_frame=False
        )
        assert result[0][0] == "11"

    def test_sa_guild_member_kept_when_bbox_misses_row(self):
        """SA non-first: guild member kept even if bbox missed its row entirely.

        Regression test for recluse (rank 74 SA) being dropped because RapidOCR
        failed to detect its dark-avatar row while Qwen read it correctly.
        """
        bot = self._bot()
        bot._guild_members = ["recluse", "Fuq"]
        # Qwen correctly reads both; bbox only sees Fuq (missed recluse's row)
        rows = [
            ("74", "recluse", None),
            ("75", "Fuq", None),
        ]
        bbox_rows = [("75", "Fuq", None)]
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=True, is_first_frame=False
        )
        names = {r[1] for r in result}
        ranks = {r[0] for r in result}
        assert "recluse" in names, (
            "recluse must be kept (guild member, non-podium rank)"
        )
        assert "74" in ranks
        assert "Fuq" in names
        assert "75" in ranks

    def test_sa_podium_hallucination_still_filtered_with_guild_members(self):
        """SA non-first: podium ranks 1/2/3 still dropped.

        Dropped even if name is a guild member.
        """
        bot = self._bot()
        bot._guild_members = ["Aurion", "Persephone"]
        # Qwen hallucinates Aurion at rank 1 (podium always visible in all frames)
        rows = [
            ("1", "Aurion", None),  # podium hallucination
            ("8", "Persephone", None),  # real entry
        ]
        bbox_rows = [("8", "Persephone", None)]
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=True, is_first_frame=False
        )
        names = {r[1] for r in result}
        assert "Aurion" not in names, "podium hallucination must still be filtered"
        assert "Persephone" in names

    def test_unconfirmed_first_frame_podium_rank_dropped_to_unranked(self):
        """DR first frame: unconfirmed rank 1 is dropped, name/score kept.

        Regression test: Aurion is the guild's top scorer and always the
        first row directly below the (permanently visible, non-scrolling)
        podium. Qwen defaults to rank 1 for that row whenever it can't read
        the actual badge digit — reproduced on every date scanned, even ones
        where Aurion's real rank was 4. Since this row only ever appears on
        the first frame (it scrolls off-screen immediately after), there's no
        later observation to outvote a wrong rank 1. bbox found nothing at
        all for ranks 1/2/3 this frame, so the claim is unconfirmed and
        should be dropped rather than reported as fact — but the name/score
        must survive as an unranked observation, not be discarded outright.
        """
        bot = self._bot()
        rows = [("1", "Aurion", "198B")]
        bbox_rows = []  # bbox saw nothing confirming rank 1/2/3 this frame
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=False, is_first_frame=True
        )
        assert result == [(None, "Aurion", "198B")]

    def test_confirmed_first_frame_podium_rank_kept(self):
        """DR first frame: rank 1 confirmed independently by bbox is kept.

        On a day Aurion's real rank genuinely was 1, bbox read the rank
        digit "1" for that row (just without managing to pair it with a
        name) — independent corroboration that should NOT be discarded.
        """
        bot = self._bot()
        rows = [("1", "Aurion", "184B")]
        bbox_rows = [("1", None, None)]  # bbox confirms rank 1 exists, no name
        result = bot._apply_bbox_rank_corrections(
            rows, bbox_rows, is_supreme_arena=False, is_first_frame=True
        )
        assert result == [("1", "Aurion", "184B")]


# ─────────────────────────────────────────────────────────────────────────────
# llm_y_min logic in _parse_rankings_rows
# ─────────────────────────────────────────────────────────────────────────────


def _make_screenshot(height: int = 1920, width: int = 1080) -> np.ndarray:
    return np.zeros((height, width, 3), dtype=np.uint8)


def _crop_height(bot, is_supreme_arena: bool, is_first_frame: bool) -> int:
    """Call _parse_rankings_rows with a mock Qwen and return the crop height."""
    screenshot = _make_screenshot()
    mock_qwen = MagicMock(spec=QwenVLOCRBackend)
    mock_qwen.extract_rankings_from_screenshot.return_value = []

    bot._rapidocr_supplement = MagicMock()
    bot._ocr_debug = None

    with patch.object(bot, "_parse_rankings_bbox", return_value=([], [], [])):
        bot._parse_rankings_rows(
            screenshot,
            mock_qwen,
            is_first_frame=is_first_frame,
            is_supreme_arena=is_supreme_arena,
        )

    crop = mock_qwen.extract_rankings_from_screenshot.call_args[0][0]
    return crop.shape[0]


class TestLlmYMinCropRegion:
    """Verify _parse_rankings_rows passes the correct crop to Qwen for each case."""

    def _bot(self):
        return _GuildScan()

    def _expected_height(self, llm_y_min: int) -> int:
        y_max = _GuildScan._Y_MAX_RANKINGS  # 1800
        return y_max - llm_y_min

    def test_sa_first_crop_starts_at_700(self):
        """SA first frame: llm_y_min = y_min = 700 (podium excluded)."""
        bot = self._bot()
        height = _crop_height(bot, is_supreme_arena=True, is_first_frame=True)
        assert height == self._expected_height(700)

    def test_sa_non_first_crop_starts_at_350(self):
        """SA non-first: llm_y_min=350; bbox_rank_set filters podium hallucinations."""
        bot = self._bot()
        height = _crop_height(bot, is_supreme_arena=True, is_first_frame=False)
        assert height == self._expected_height(350)

    def test_dr_first_crop_starts_at_450(self):
        """DR first frame: llm_y_min=450 (skips artistic header)."""
        bot = self._bot()
        height = _crop_height(bot, is_supreme_arena=False, is_first_frame=True)
        assert height == self._expected_height(450)

    def test_dr_non_first_crop_starts_at_350(self):
        """DR non-first: llm_y_min=350 (max context prevents Cyrillic mode)."""
        bot = self._bot()
        height = _crop_height(bot, is_supreme_arena=False, is_first_frame=False)
        assert height == self._expected_height(350)


# ─────────────────────────────────────────────────────────────────────────────
# Supplemental null-rank filter (SA non-first)
# ─────────────────────────────────────────────────────────────────────────────


class TestSupplementalNullRankFilter:
    """SA non-first: bbox supplementals with null rank must be filtered out."""

    def _bot(self):
        return _GuildScan()

    def _run_parse(
        self, bot, is_supreme_arena: bool, is_first_frame: bool, qwen_rows, bbox_rows
    ):
        screenshot = _make_screenshot()
        mock_qwen = MagicMock(spec=QwenVLOCRBackend)
        mock_qwen.extract_rankings_from_screenshot.return_value = qwen_rows
        bot._rapidocr_supplement = MagicMock()
        bot._ocr_debug = None
        with patch.object(
            bot, "_parse_rankings_bbox", return_value=(bbox_rows, [], [])
        ):
            return bot._parse_rankings_rows(
                screenshot,
                mock_qwen,
                is_first_frame=is_first_frame,
                is_supreme_arena=is_supreme_arena,
            )

    def test_sa_non_first_null_rank_supplemental_dropped(self):
        """Null-rank bbox supplement for SA non-first is not added to output."""
        bot = self._bot()
        # We need Sebv NOT already in llm_rank_names after correction to test supplement
        # Simplest: use a different name
        qwen_rows2 = [("7", "Night-", None)]
        bbox_rows2 = [(None, "Sebv", None)]  # Sebv visible but no rank badge

        # Patch guild_members to include Sebv
        bot._guild_members = ["Sebv", "Night-"]

        result = self._run_parse(
            bot,
            is_supreme_arena=True,
            is_first_frame=False,
            qwen_rows=qwen_rows2,
            bbox_rows=bbox_rows2,
        )
        # Sebv should NOT appear (null-rank supplement filtered for SA non-first)
        assert not any(r[1] == "Sebv" for r in result)

    def test_sa_non_first_ranked_supplemental_kept(self):
        """Bbox supplement with actual rank IS kept for SA non-first."""
        bot = self._bot()
        qwen_rows = [("7", "Night-", None)]
        # Sebv has a rank confirmed by bbox → should be supplemented
        bbox_rows = [("12", "Sebv", None)]
        bot._guild_members = ["Sebv", "Night-"]

        result = self._run_parse(
            bot,
            is_supreme_arena=True,
            is_first_frame=False,
            qwen_rows=qwen_rows,
            bbox_rows=bbox_rows,
        )
        sebv_entries = [r for r in result if r[1] == "Sebv"]
        assert len(sebv_entries) >= 1
        assert sebv_entries[0][0] == "12"


# ─────────────────────────────────────────────────────────────────────────────
# _torch_metadata
# ─────────────────────────────────────────────────────────────────────────────


def _make_dist_info(tmp_path: Path, version: str) -> None:
    dist_info = tmp_path / f"torch-{version}.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(f"Metadata-Version: 2.1\nVersion: {version}\n")


# ─────────────────────────────────────────────────────────────────────────────
# _recover_supplement_names_qwen — fuzzy fallback
# ─────────────────────────────────────────────────────────────────────────────


class TestRecoverSupplementNamesQwen:
    """_recover_supplement_names_qwen falls back to fuzzy matching."""

    def _bot(self):
        return _GuildScan()

    def test_fuzzy_match_used_when_exact_match_fails(self):
        """Garbled Cyrillic from Qwen is recovered via fuzzy matching."""
        bot = self._bot()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)
        guild_set = {"ОпасныйПоцык", "Sacrifar"}

        garbled = "OnacHbINlo1IbIK"
        bbox_debug = [
            {
                "name": garbled,
                "rank": "29",
                "blocks": [
                    {
                        "text": garbled,
                        "cx": 330,
                        "cy": 500,
                        "col": "name_guild",
                    }
                ],
            }
        ]
        supplemental: list = []
        mock_qwen = MagicMock(spec=QwenVLOCRBackend)
        mock_qwen.extract_player_name.return_value = garbled

        with patch.object(bot, "_correct_single_name", return_value="ОпасныйПоцык"):
            bot._recover_supplement_names_qwen(
                screenshot, bbox_debug, guild_set, supplemental, mock_qwen
            )

        assert len(supplemental) == 1
        assert supplemental[0][0] == "29"
        assert supplemental[0][1] == "ОпасныйПоцык"

    def test_no_entry_when_fuzzy_returns_same_as_input(self):
        """If fuzzy returns the same string, nothing is added."""
        bot = self._bot()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)
        guild_set = {"ОпасныйПоцык", "Sacrifar"}

        unknown = "CompletelyUnknownPlayer"
        bbox_debug = [
            {
                "name": unknown,
                "rank": "99",
                "blocks": [
                    {
                        "text": unknown,
                        "cx": 330,
                        "cy": 500,
                        "col": "name_guild",
                    }
                ],
            }
        ]
        supplemental: list = []
        mock_qwen = MagicMock(spec=QwenVLOCRBackend)
        mock_qwen.extract_player_name.return_value = unknown

        with patch.object(bot, "_correct_single_name", return_value=unknown):
            bot._recover_supplement_names_qwen(
                screenshot, bbox_debug, guild_set, supplemental, mock_qwen
            )

    def test_skips_recovery_when_bbox_name_matches_ignoring_pipe_spacing(self):
        """A row bbox already read correctly must not be re-asked and overridden.

        Regression: bbox read "CTL|Arsenal" (no space) for a row while the
        guild roster stores "CTL | Arsenal" (with space). An exact-string
        membership check treated this as an unrecognized name and re-asked
        Qwen on an isolated crop of that same row — which then misread it as
        a completely different member ("CTL | 춉춉"), overriding an already
        correct reading via the supplemental x3 weighting in canonicalization.
        """
        bot = self._bot()
        screenshot = np.zeros((1920, 1080, 3), dtype=np.uint8)
        guild_set = {"CTL | Arsenal", "Sacrifar"}

        bbox_debug = [
            {
                "name": "CTL|Arsenal",
                "rank": "18",
                "blocks": [
                    {
                        "text": "CTL|ArsenalG434",
                        "cx": 450,
                        "cy": 1440,
                        "col": "name_guild",
                    }
                ],
            }
        ]
        supplemental: list = []
        mock_qwen = MagicMock(spec=QwenVLOCRBackend)
        mock_qwen.extract_player_name.return_value = "CTL | 춉춉"

        bot._recover_supplement_names_qwen(
            screenshot, bbox_debug, guild_set, supplemental, mock_qwen
        )

        mock_qwen.extract_player_name.assert_not_called()
        assert supplemental == []

        assert len(supplemental) == 0


class TestTorchMetadata:
    def test_cuda_only(self, tmp_path):
        _make_dist_info(tmp_path, "2.12.0+cu126")
        with patch.object(_GuildScanSetupMixin, "_extras_dir", return_value=tmp_path):
            has_cuda, ver = _GuildScanSetupMixin._torch_metadata()
        assert has_cuda is True
        assert ver == (2, 12)

    def test_cpu_only(self, tmp_path):
        _make_dist_info(tmp_path, "2.12.0")
        with patch.object(_GuildScanSetupMixin, "_extras_dir", return_value=tmp_path):
            has_cuda, ver = _GuildScanSetupMixin._torch_metadata()
        assert has_cuda is False
        assert ver == (2, 12)

    def test_both_cpu_and_cuda_prefers_cuda(self, tmp_path):
        _make_dist_info(tmp_path, "2.12.0")
        _make_dist_info(tmp_path, "2.12.0+cu126")
        with patch.object(_GuildScanSetupMixin, "_extras_dir", return_value=tmp_path):
            has_cuda, ver = _GuildScanSetupMixin._torch_metadata()
        assert has_cuda is True
        assert ver == (2, 12)

    def test_missing_returns_false(self, tmp_path):
        with patch.object(_GuildScanSetupMixin, "_extras_dir", return_value=tmp_path):
            has_cuda, ver = _GuildScanSetupMixin._torch_metadata()
        assert has_cuda is False
        assert ver == (0, 0)


# ─────────────────────────────────────────────────────────────────────────────
# _normalize_phase_tab_text (AFK Stage Season Phase Rankings)
# ─────────────────────────────────────────────────────────────────────────────


class TestNormalizePhaseTabText:
    def _bot(self):
        return _GuildScan()

    def test_plain_phase_number(self):
        bot = self._bot()
        assert bot._normalize_phase_tab_text("Phase 2") == "Phase 2"

    def test_ocr_misread_digit_as_letter_l(self):
        """RapidOCR sometimes reads the '1' in 'Phase 1' as a lowercase L."""
        bot = self._bot()
        assert bot._normalize_phase_tab_text("Phase l") == "Phase 1"

    def test_ocr_misread_digit_as_letter_i(self):
        bot = self._bot()
        assert bot._normalize_phase_tab_text("Phase I") == "Phase 1"

    def test_multi_digit_phase_number(self):
        bot = self._bot()
        assert bot._normalize_phase_tab_text("Phase 10") == "Phase 10"

    def test_unrelated_sidebar_labels_are_not_phase_tabs(self):
        bot = self._bot()
        for text in ("1st Clear", "Season", "Phase Progress", "Cleared", "Phase"):
            assert bot._normalize_phase_tab_text(text) is None


# ─────────────────────────────────────────────────────────────────────────────
# _parse_single_row score column (digit-filter + multi-block join)
# ─────────────────────────────────────────────────────────────────────────────


def _ocr_result(text: str, cx: int, cy: int) -> OCRResult:
    box = Box(Point(max(cx - 40, 0), max(cy - 15, 0)), 80, 30)
    return OCRResult(text=text, confidence=ConfidenceValue("90%"), box=box)


class TestParseSingleRowScoreColumn:
    def _bot(self):
        return _GuildScan()

    def test_non_digit_label_excluded_from_score(self):
        """'Phase Progress' shares the score column but has no digits."""
        bot = self._bot()
        row = [
            _ocr_result("1", 100, 900),
            _ocr_result("Holymes", 400, 900),
            _ocr_result("Phase Progress", 945, 874),
            _ocr_result("981", 947, 928),
        ]
        rank, name, score = bot._parse_single_row(
            row, screenshot=None, ocr_backend=None
        )
        assert rank == "1"
        assert name == "Holymes"
        assert score == "981"

    def test_split_date_and_time_joined_in_reading_order(self):
        """A completed AFK Stage phase shows 'Cleared' + date + time as 3 blocks."""
        bot = self._bot()
        row = [
            _ocr_result("1", 100, 885),
            _ocr_result("Mikki", 400, 885),
            _ocr_result("Cleared", 945, 872),
            _ocr_result("2026-06-16", 947, 910),
            _ocr_result("19:05", 947, 944),
        ]
        rank, name, score = bot._parse_single_row(
            row, screenshot=None, ocr_backend=None
        )
        assert rank == "1"
        assert name == "Mikki"
        assert score == "2026-06-16 19:05"

    def test_season_label_still_excluded(self):
        """Regression: Supreme Arena's 'Season' label must still be dropped."""
        bot = self._bot()
        row = [
            _ocr_result("3", 100, 900),
            _ocr_result("BST | Arsenal", 400, 900),
            _ocr_result("Season", 945, 874),
            _ocr_result("972", 947, 928),
        ]
        _, _, score = bot._parse_single_row(row, screenshot=None, ocr_backend=None)
        assert score == "972"


# ─────────────────────────────────────────────────────────────────────────────
# _extract_player_name (name vs. guild-slot-code same-line tie-break)
# ─────────────────────────────────────────────────────────────────────────────


class TestExtractPlayerNameSameLineTieBreak:
    def _bot(self):
        return _GuildScan()

    def test_name_wins_over_guild_code_split_on_same_line(self):
        """Regression: Aurion's row split "Aurion" / "G439" onto near-identical Y.

        Real coordinates from a Dream Realm scan: the name and its guild-slot
        code landed as two separate blocks 2px apart in Y instead of merging
        into one ("AurionG439"). Picking by Y alone chose "G439" (marginally
        smaller Y), which the suffix-strip then reduced to "" — dropping the
        row (score 208B, rank 3) entirely.
        """
        bot = self._bot()
        row = [
            _ocr_result("3", 99, 905),
            _ocr_result("Aurion", 378, 885),
            _ocr_result("G439", 483, 883),
            _ocr_result("CITADEL", 426, 942),
            _ocr_result("208B", 913, 929),
            _ocr_result("Season", 923, 873),
        ]
        rank, name, score = bot._parse_single_row(
            row, screenshot=None, ocr_backend=None
        )
        assert rank == "3"
        assert name == "Aurion"
        assert score == "208B"

    def test_name_wins_over_guild_code_split_short_name(self):
        """Same bug, short numeric-looking name: "67" vs "G433" split on one line."""
        bot = self._bot()
        row = [
            _ocr_result("35", 101, 1686),
            _ocr_result("67", 333, 1664),
            _ocr_result("G433", 393, 1663),
            _ocr_result("CITADEL", 426, 1721),
            _ocr_result("195B", 913, 1709),
            _ocr_result("Season", 921, 1652),
        ]
        rank, name, score = bot._parse_single_row(
            row, screenshot=None, ocr_backend=None
        )
        assert rank == "35"
        assert name == "67"
        assert score == "195B"


# ─────────────────────────────────────────────────────────────────────────────
# _find_phase_tabs
# ─────────────────────────────────────────────────────────────────────────────


class TestFindPhaseTabs:
    def _bot(self):
        return _GuildScan()

    def test_finds_and_orders_tabs_left_to_right(self):
        bot = self._bot()
        ocr_backend = MagicMock()
        ocr_backend.detect_text_blocks.return_value = [
            _ocr_result("Phase l", 803, 746),
            _ocr_result("Phase 2", 349, 746),
            _ocr_result("1st Clear", 974, 379),
            _ocr_result("Season Phase Rankings", 334, 66),
        ]
        bot.get_screenshot = MagicMock(return_value=np.zeros((1, 1, 3)))
        tabs = bot._find_phase_tabs(ocr_backend)
        assert [name for name, _ in tabs] == ["Phase 2", "Phase 1"]


# ─────────────────────────────────────────────────────────────────────────────
# _scan_visible_phase_tabs (target phase selection: 1..N, not "N most recent")
# ─────────────────────────────────────────────────────────────────────────────


class TestScanVisiblePhaseTabs:
    def _bot(self):
        bot = _GuildScan()
        bot.tap = MagicMock()
        bot._set_guild_members_filter = MagicMock(return_value=True)
        bot._scan_rankings_for_current_date = MagicMock(return_value=[])
        bot._correct_names_with_guild_members = MagicMock(return_value=[])
        return bot

    def test_phases_to_scan_one_only_processes_phase_one(self):
        """Setting=1 must scan Phase 1, not the current/highest-numbered phase."""
        bot = self._bot()
        phase_tabs = [
            ("Phase 2", _ocr_result("Phase 2", 349, 746)),
            ("Phase 1", _ocr_result("Phase 1", 803, 746)),
        ]
        processed: set[str] = set()
        bot._scan_visible_phase_tabs(
            phase_tabs, processed, {"Phase 1"}, [], MagicMock(), None, []
        )
        assert processed == {"Phase 1"}
        bot._scan_rankings_for_current_date.assert_called_once()
        assert bot._scan_rankings_for_current_date.call_args[0][0] == "Phase 1"

    def test_phases_to_scan_two_processes_phase_one_and_two(self):
        bot = self._bot()
        phase_tabs = [
            ("Phase 2", _ocr_result("Phase 2", 349, 746)),
            ("Phase 1", _ocr_result("Phase 1", 803, 746)),
        ]
        processed: set[str] = set()
        bot._scan_visible_phase_tabs(
            phase_tabs, processed, {"Phase 1", "Phase 2"}, [], MagicMock(), None, []
        )
        assert processed == {"Phase 1", "Phase 2"}

    def test_already_processed_phase_is_skipped(self):
        bot = self._bot()
        phase_tabs = [("Phase 1", _ocr_result("Phase 1", 803, 746))]
        processed = {"Phase 1"}
        bot._scan_visible_phase_tabs(
            phase_tabs, processed, {"Phase 1"}, [], MagicMock(), None, []
        )
        bot._scan_rankings_for_current_date.assert_not_called()
