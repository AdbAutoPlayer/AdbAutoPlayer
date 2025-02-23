import unittest
from pathlib import Path

import adb_auto_player.template_matching as template_matching

TEST_DATA_DIR = Path(__file__).parent / "data"


class TestTemplateMatching(unittest.TestCase):
    def test_similar_image_templates(self):
        f1 = TEST_DATA_DIR / "records_formation_1.png"
        f2 = TEST_DATA_DIR / "records_formation_2.png"
        f5 = TEST_DATA_DIR / "records_formation_5.png"
        f6 = TEST_DATA_DIR / "records_formation_6.png"
        f7 = TEST_DATA_DIR / "records_formation_7.png"

        result = template_matching.similar_image(
            base_image=template_matching.load_image(f1),
            template_image=template_matching.load_image(f1),
        )
        self.assertTrue(result)

        result = template_matching.similar_image(
            base_image=template_matching.load_image(f1),
            template_image=template_matching.load_image(f2),
        )
        self.assertFalse(result)
