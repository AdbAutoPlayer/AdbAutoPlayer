import pytest
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.template_matching import MatchResult, TemplateMatchResult


class TestMatchResult:
    @pytest.fixture
    def sample_box(self):
        return Box(Point(10, 20), width=30, height=40)

    @pytest.fixture
    def sample_confidence(self):
        return ConfidenceValue(0.95)

    @pytest.fixture
    def match_result(self, sample_box, sample_confidence):
        return MatchResult(box=sample_box, confidence=sample_confidence)

    def test_creation(self, match_result, sample_box, sample_confidence):
        assert match_result.box == sample_box
        assert match_result.confidence == sample_confidence

    def test_with_offset(self, match_result):
        offset = Point(x=5, y=3)
        new_result = match_result.with_offset(offset)
        expected_box = match_result.box.with_offset(offset)

        assert new_result is not match_result
        assert new_result.box == expected_box
        assert new_result.confidence == match_result.confidence

    def test_to_template_match_result(self, match_result):
        template = "example_template"
        result = match_result.to_template_match_result(template)

        assert isinstance(result, TemplateMatchResult)
        assert result.box == match_result.box
        assert result.confidence == match_result.confidence
        assert result.template == template

    def test_str(self, match_result):
        result_str = str(match_result)
        assert "MatchResult" in result_str
        assert str(match_result.box) in result_str
        assert str(match_result.confidence) in result_str

    def test_x_property(self, match_result):
        assert match_result.x == match_result.box.x

    def test_y_property(self, match_result):
        assert match_result.y == match_result.box.y
