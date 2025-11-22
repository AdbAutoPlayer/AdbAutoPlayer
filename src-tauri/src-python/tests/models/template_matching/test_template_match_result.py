import unittest

from adb_auto_player.models import ConfidenceValue
from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.template_matching import TemplateMatchResult


class TestTemplateMatchResult(unittest.TestCase):
    def setUp(self):
        self.template = "test_template"
        self.confidence = 0.85
        self.top_left = Point(10, 20)
        self.box = Box(self.top_left, width=30, height=40)
        self.result = TemplateMatchResult(
            self.template, ConfidenceValue(self.confidence), self.box
        )

    def test_str(self):
        expected_str = (
            f"TemplateMatchResult(template='{self.template}', "
            f"confidence={ConfidenceValue(self.confidence)}, box={self.box})"
        )
        self.assertEqual(str(self.result), expected_str)

    def test_with_offset(self):
        offset = Point(5, 3)
        new_result = self.result.with_offset(offset)

        # Check that the original is unchanged
        self.assertEqual(self.result.box.top_left.x, 10)
        self.assertEqual(self.result.box.top_left.y, 20)

        # Check the offset was applied correctly
        self.assertEqual(new_result.box.top_left.x, 15)
        self.assertEqual(new_result.box.top_left.y, 23)

        # Check width and height are unchanged
        self.assertEqual(new_result.box.width, self.box.width)
        self.assertEqual(new_result.box.height, self.box.height)

        # Check other attributes are unchanged
        self.assertEqual(new_result.template, self.template)
        self.assertEqual(new_result.confidence, self.confidence)

        # Check that a new instance is returned (immutability)
        self.assertIsNot(new_result, self.result)
        self.assertIsNot(new_result.box, self.result.box)


if __name__ == "__main__":
    unittest.main()
