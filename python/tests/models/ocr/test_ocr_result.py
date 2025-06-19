import unittest

from adb_auto_player.models.geometry import Box, Point
from adb_auto_player.models.ocr import OCRResult


class TestOCRResult(unittest.TestCase):
    def setUp(self):
        self.text = "example"
        self.confidence = 0.85
        self.top_left = Point(10, 20)
        self.width = 100
        self.height = 50
        self.box = Box(self.top_left, self.width, self.height)
        self.ocr_result = OCRResult(self.text, self.confidence, self.box)

    def test_str(self):
        expected_str = (
            f"OCRResult(text='{self.text}', confidence={self.confidence:.2f}, "
            f"box={self.box})"
        )
        self.assertEqual(str(self.ocr_result), expected_str)

    def test_with_offset(self):
        offset = Point(5, 7)
        new_ocr = self.ocr_result.with_offset(offset)

        # Check text and confidence remain unchanged
        self.assertEqual(new_ocr.text, self.text)
        self.assertEqual(new_ocr.confidence, self.confidence)

        # Check box coordinates are offset correctly
        expected_top_left = Point(
            self.top_left.x + offset.x, self.top_left.y + offset.y
        )
        self.assertEqual(new_ocr.box.top_left, expected_top_left)
        self.assertEqual(new_ocr.box.width, self.width)
        self.assertEqual(new_ocr.box.height, self.height)

        # Check that original OCRResult box remains unchanged (immutability)
        self.assertEqual(self.ocr_result.box.top_left, self.top_left)


if __name__ == "__main__":
    unittest.main()
