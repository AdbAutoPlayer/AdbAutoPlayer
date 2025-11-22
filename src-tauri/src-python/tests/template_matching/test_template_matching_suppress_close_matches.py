from adb_auto_player.template_matching.template_matcher import _suppress_close_matches


class TestSuppressCloseMatches:
    """Tests for _suppress_close_matches function."""

    def test_suppress_close_matches(self):
        """Test suppressing matches within minimum distance."""
        matches = [(10, 10), (15, 15), (100, 100), (105, 105)]
        min_distance = 10

        result = _suppress_close_matches(matches, min_distance)

        # Should keep only distant matches
        assert len(result) == 2
        assert (10, 10) in result
        assert (100, 100) in result

    def test_empty_matches_returns_empty(self):
        """Test that empty input returns empty list."""
        result = _suppress_close_matches([], 10)
        assert result == []

    def test_single_match_returns_single(self):
        """Test that single match returns unchanged."""
        matches = [(50, 50)]
        result = _suppress_close_matches(matches, 10)
        assert result == [(50, 50)]

    def test_all_matches_far_apart(self):
        """Test that all matches far apart are kept."""
        matches = [(10, 10), (50, 50), (100, 100), (150, 150)]
        min_distance = 20

        result = _suppress_close_matches(matches, min_distance)

        assert len(result) == 4
        assert set(result) == set(matches)
