from pathlib import Path

from adb_auto_player.image_manipulation import load_image
from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.template_matching import MatchResult
from adb_auto_player.template_matching import (
    find_all_template_matches,
    find_template_match,
    similar_image,
)


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_workflow_find_and_verify(self):
        """Test a complete workflow of finding and verifying matches."""
        base_image = load_image(
            Path(__file__).parent / "data" / "guitar_girl_with_notes.png"
        )
        template = load_image(Path(__file__).parent / "data" / "small_note.png")

        result = find_template_match(
            base_image,
            template,
            threshold=ConfidenceValue("100%"),
        )
        assert isinstance(result, MatchResult)

        x, y = result.box.top_left.to_tuple()
        w, h = result.box.width, result.box.height
        found_image = base_image[y : y + h, x : x + w]
        is_similar = similar_image(template, found_image, ConfidenceValue("95%"))
        assert is_similar is True

        all_matches = find_all_template_matches(
            base_image, template, ConfidenceValue("100%"), min_distance=50
        )
        assert len(all_matches) == 1

        all_matches = find_all_template_matches(
            base_image, template, ConfidenceValue("80%"), min_distance=50
        )
        assert len(all_matches) > 1
