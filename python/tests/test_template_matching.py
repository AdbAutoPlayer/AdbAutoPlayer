import unittest
from pathlib import Path

import adb_auto_player.template_matching as template_matching

TEST_DATA_DIR = Path(__file__).parent / "data"


class TestTemplateMatching(unittest.TestCase):
    def test_compare_roi_similarity(self):
        f1 = TEST_DATA_DIR / "records_formation_1.png"
        f2 = TEST_DATA_DIR / "records_formation_2.png"
        f5 = TEST_DATA_DIR / "records_formation_5.png"
        f6 = TEST_DATA_DIR / "records_formation_6.png"
        f7 = TEST_DATA_DIR / "records_formation_7.png"

        # coordinates cannot be negative
        with self.assertRaises(ValueError):
            template_matching.compare_roi_similarity(
                template_matching.load_image(f1),
                template_matching.load_image(f1),
                (-1, -1, -1, -1),
            )

        # sx and sy need to be smaller than ex and ey
        with self.assertRaises(ValueError):
            template_matching.compare_roi_similarity(
                template_matching.load_image(f1),
                template_matching.load_image(f1),
                (1, 1, 1, 1),
            )

        # sx and sy greater than ex and ey
        with self.assertRaises(ValueError):
            template_matching.compare_roi_similarity(
                template_matching.load_image(f1),
                template_matching.load_image(f1),
                (2, 2, 1, 1),
            )

        # ey larger than base_image height
        with self.assertRaises(ValueError):
            template_matching.compare_roi_similarity(
                template_matching.load_image(f1),
                template_matching.load_image(f1),
                (0, 0, 1, 1921),
            )

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
