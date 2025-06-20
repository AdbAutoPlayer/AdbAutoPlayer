"""Unit tests for OCR backends with performance benchmarking."""

import unittest

from adb_auto_player.ocr import OEM, PSM, TesseractBackend, TesseractConfig


class TestTesseractBackendInfo(unittest.TestCase):
    """Test cases for OCR backend implementations."""

    def test_tesseract_backend_info_default(self) -> None:
        tesseract_backend = TesseractBackend()
        info = tesseract_backend.get_backend_info()
        self.assertNotEqual(info["version"], "Unknown")
        self.assertEqual(info["name"], "Tesseract")
        self.assertIn("eng", info["supported_languages"])
        self.assertEqual(info["config"].oem, OEM.DEFAULT)
        self.assertEqual(info["config"].psm, PSM.DEFAULT)

    def test_tesseract_backend_info_custom_config(self) -> None:
        tesseract_backend = TesseractBackend(
            config=TesseractConfig(
                oem=OEM.LEGACY,
                psm=PSM.AUTO_PSM_NO_OSD,
            ),
        )
        info = tesseract_backend.get_backend_info()
        self.assertNotEqual(info["version"], "Unknown")
        self.assertEqual(info["name"], "Tesseract")
        self.assertIn("eng", info["supported_languages"])
        self.assertEqual(info["config"].oem, OEM.LEGACY)
        self.assertEqual(info["config"].psm, PSM.AUTO_PSM_NO_OSD)
