"""Unit tests for OCR backends with performance benchmarking."""

import unittest
from unittest.mock import patch

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

    @patch("adb_auto_player.ocr.tesseract_backend._initialize_tesseract")
    @patch("pytesseract.get_tesseract_version")
    def test_get_backend_info_success(self, mock_get_version, mock_init):
        """Test get_backend_info with successful version retrieval."""
        mock_get_version.return_value = "5.3.0"

        backend = TesseractBackend()

        with patch.object(backend, "_get_supported_languages") as mock_langs:
            mock_langs.return_value = ["eng", "chi_sim", "jpn"]

            info = backend.get_backend_info()

            assert info["name"] == "Tesseract"
            assert info["version"] == "5.3.0"
            assert info["config"] == backend.config
            assert info["supported_languages"] == ["eng", "chi_sim", "jpn"]

    @patch("adb_auto_player.ocr.tesseract_backend._initialize_tesseract")
    @patch("adb_auto_player.ocr.tesseract_backend.pytesseract.get_tesseract_version")
    def test_get_backend_info_version_error(self, mock_get_version, mock_init):
        """Test get_backend_info handles version retrieval errors."""
        mock_get_version.side_effect = Exception("Version error")

        backend = TesseractBackend()

        with patch.object(backend, "_get_supported_languages") as mock_langs:
            mock_langs.return_value = ["eng"]

            info = backend.get_backend_info()

            assert info["version"] == "Unknown"

    @patch("adb_auto_player.ocr.tesseract_backend._initialize_tesseract")
    @patch("pytesseract.get_languages")
    @patch("adb_auto_player.ocr.tesseract_lang.Lang.get_supported_languages")
    def test_get_supported_languages_fallback(
        self, mock_lang_fallback, mock_get_languages, mock_init
    ):
        """Test _get_supported_languages falls back to Lang enum on error."""
        mock_get_languages.side_effect = Exception("Language retrieval error")
        mock_lang_fallback.return_value = ["eng"]

        backend = TesseractBackend()
        languages = backend._get_supported_languages()

        assert languages == ["eng"]
        mock_lang_fallback.assert_called_once()

    @patch("adb_auto_player.ocr.tesseract_backend._initialize_tesseract")
    @patch("pytesseract.get_languages")
    def test_get_supported_languages_success(self, mock_get_languages, mock_init):
        """Test _get_supported_languages with successful retrieval."""
        mock_get_languages.return_value = ["eng", "fra", "deu", "spa"]

        backend = TesseractBackend()
        languages = backend._get_supported_languages()

        assert languages == ["deu", "eng", "fra", "spa"]  # Should be sorted
        mock_get_languages.assert_called_once_with(config=backend.config.config_string)
