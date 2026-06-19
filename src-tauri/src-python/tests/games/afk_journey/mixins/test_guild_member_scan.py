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
