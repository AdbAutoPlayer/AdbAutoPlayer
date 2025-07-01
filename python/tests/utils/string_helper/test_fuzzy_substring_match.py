import pytest
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.util import StringHelper


class TestFuzzySubstringMatch:
    """Test cases for StringHelper.fuzzy_substring_match method."""

    @pytest.mark.parametrize(
        "text,pattern,threshold,expected",
        [
            # Exact matches
            ("hello world", "hello", "80%", True),
            ("hello world", "world", "80%", True),
            ("HELLO WORLD", "hello", "80%", True),  # case insensitive
            ("hello world", "HELLO", "80%", True),  # case insensitive
            # Fuzzy matches
            ("hello world", "hallo", "90%", False),  # below threshold
            ("hello world", "hallo", "70%", True),  # above threshold
            ("hello world", "hellx", "90%", False),  # below threshold
            ("hello world", "hellx", "75%", True),  # above threshold
            # Partial matches
            ("hello world", "hello worl", "80%", True),
            ("hello world", "ello wor", "80%", True),
            # Edge cases
            ("hello world", "", "80%", True),  # empty pattern
            ("", "hello", "80%", False),  # empty text
            ("short", "longer text", "80%", False),  # pattern longer than text
            # Threshold tests
            ("hello world", "h3llo", "60%", True),
            ("hello world", "h3llo", "70%", True),
            ("hello world", "he11o", "50%", True),
            ("hello world", "he11o", "80%", False),
        ],
    )
    def test_fuzzy_substring_match(self, text, pattern, threshold, expected):
        """Test fuzzy substring matching with various scenarios."""
        threshold = ConfidenceValue(threshold)
        assert StringHelper.fuzzy_substring_match(text, pattern, threshold) == expected

    def test_default_threshold(self):
        """Test that the default threshold of 80% works as expected."""
        # Should match at 80%
        assert StringHelper.fuzzy_substring_match("hello world", "hello") is True
        # Should match at 80%
        assert StringHelper.fuzzy_substring_match("hello world", "hallo") is True
        # Should not match at 90%
        assert (
            StringHelper.fuzzy_substring_match(
                "hello world", "hallo", ConfidenceValue("90%")
            )
            is False
        )
