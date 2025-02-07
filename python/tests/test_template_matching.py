import unittest
from pathlib import Path

import adb_auto_player.template_matching as template_matching


class TestTemplateMatching(unittest.TestCase):
    def test_compare_roi_similarity(self):
        f1 = Path("data/records_formation_1.png")
        f2 = Path("data/records_formation_2.png")
        f5 = Path("data/records_formation_5.png")
        f6 = Path("data/records_formation_6.png")
        f7 = Path("data/records_formation_7.png")

        roi = (450, 280, 780, 400)
        result = template_matching.compare_roi_similarity(
            template_matching.load_image(f1), template_matching.load_image(f1), roi
        )
        self.assertTrue(result)

        result = template_matching.compare_roi_similarity(
            template_matching.load_image(f1), template_matching.load_image(f2), roi
        )
        self.assertFalse(result)

        result = template_matching.compare_roi_similarity(
            template_matching.load_image(f5), template_matching.load_image(f6), roi
        )
        self.assertFalse(result)

        result = template_matching.compare_roi_similarity(
            template_matching.load_image(f6), template_matching.load_image(f7), roi
        )
        self.assertFalse(result)

        result = template_matching.compare_roi_similarity(
            template_matching.load_image(f7), template_matching.load_image(f7), roi
        )
        self.assertTrue(result)
