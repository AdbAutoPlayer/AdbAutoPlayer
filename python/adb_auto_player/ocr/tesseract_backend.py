"""Tesseract OCR backend implementation."""

import os
import platform
from typing import Any

import numpy as np
import pytesseract
from adb_auto_player.models.geometry.box import Box
from adb_auto_player.models.ocr.ocr_result import OCRResult
from pytesseract import TesseractNotFoundError

from .. import ConfigLoader
from .tesseract_config import TesseractConfig
from .tesseract_lang import Lang

_NUM_COLORS_IN_RGB = 3


class TesseractBackend:
    """Tesseract OCR backend implementation."""

    def __init__(self, config: TesseractConfig = TesseractConfig()):
        """Initialize Tesseract backend.

        Args:
            config: TesseractConfig instance
        """
        self.config = config

        try:
            pytesseract.get_tesseract_version()
        except TesseractNotFoundError as e:
            if platform.system() != "Windows":
                raise RuntimeError(f"Tesseract not found in PATH: {e}")

            fallback_path = (
                ConfigLoader().binaries_dir / "windows" / "tesseract" / "tesseract.exe"
            )

            if not os.path.isfile(fallback_path):
                raise RuntimeError(f"Tesseract binaries not found in: {fallback_path}")

            pytesseract.pytesseract.tesseract_cmd = fallback_path
            try:
                pytesseract.get_tesseract_version()
            except Exception as e:
                raise RuntimeError(f"Tesseract fallback failed: {e}")

        except Exception as e:
            raise e

    def extract_text(
        self,
        image: np.ndarray,
        config_override: TesseractConfig | None = None,
    ) -> str:
        """Extract all text from an image as a single string.

        Args:
            image: Input RGB image as numpy array
            config_override: Optional TesseractConfig override

        Returns:
            str: Extracted text
        """
        if not config_override:
            config_override = self.config

        text = pytesseract.image_to_string(
            image=image,
            config=config_override.config_string,
            lang=config_override.lang_string,
        ).strip()

        return text

    def detect_text(self, image: np.ndarray, **kwargs) -> list[OCRResult]:
        """Detect text and return results with bounding boxes.

        Args:
            image: Input RGB image as numpy array
            **kwargs: Additional arguments (config, lang, min_confidence)

        Returns:
            list[OCRResult]: List of OCR results with bounding boxes
        """
        min_confidence = kwargs.get("min_confidence", 0.0)

        data = pytesseract.image_to_data(
            image,
            config=self.config.config_string,
            lang=self.config.lang_string,
            output_type=pytesseract.Output.DICT,
        )

        results = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            # Skip empty text and low confidence results
            text = data["text"][i].strip()
            confidence = float(data["conf"][i])
            # Convert confidence from 0-100 to 0-1 scale
            confidence_normalized = confidence / 100.0

            if not text or confidence_normalized < min_confidence:
                continue

            # Extract bounding box coordinates
            x = int(data["left"][i])
            y = int(data["top"][i])
            width = int(data["width"][i])
            height = int(data["height"][i])

            try:
                box = Box(x=x, y=y, width=width, height=height)

                result = OCRResult(text=text, confidence=confidence_normalized, box=box)
                results.append(result)

            except ValueError:
                # Skip invalid boxes
                continue

        return results

    def detect_text_blocks(self, image: np.ndarray, **kwargs) -> list[OCRResult]:
        """Detect text blocks and return results with bounding boxes.

        Text blocks are larger groupings of text, typically paragraphs or
        coherent sections of text, rather than individual words.

        Args:
            image: Input RGB image as numpy array
            **kwargs: Additional arguments (config, lang, min_confidence, level)

        Returns:
            list[OCRResult]: List of OCR results with text block bounding boxes
        """
        min_confidence = kwargs.get("min_confidence", 0.0)
        # Level 2 = blocks, Level 3 = paragraphs, Level 4 = lines
        level = kwargs.get("level", 2)  # Default to block level

        data = pytesseract.image_to_data(
            image,
            config=self.config.config_string,
            lang=self.config.lang_string,
            output_type=pytesseract.Output.DICT,
        )

        # Group by the specified level (block_num, par_num, etc.)
        blocks = {}
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = data["text"][i].strip()
            confidence = float(data["conf"][i])
            confidence_normalized = confidence / 100.0

            if not text or confidence_normalized < min_confidence:
                continue

            # Create grouping key based on level
            if level == 2:  # Block level
                group_key = (data["page_num"][i], data["block_num"][i])
            elif level == 3:  # Paragraph level
                group_key = (
                    data["page_num"][i],
                    data["block_num"][i],
                    data["par_num"][i],
                )
            elif level == 4:  # Line level
                group_key = (
                    data["page_num"][i],
                    data["block_num"][i],
                    data["par_num"][i],
                    data["line_num"][i],
                )
            else:
                # Default to block level
                group_key = (data["page_num"][i], data["block_num"][i])

            if group_key not in blocks:
                blocks[group_key] = {
                    "texts": [],
                    "confidences": [],
                    "left": [],
                    "top": [],
                    "right": [],
                    "bottom": [],
                }

            # Collect text and bounding box info
            blocks[group_key]["texts"].append(text)
            blocks[group_key]["confidences"].append(confidence_normalized)

            left = int(data["left"][i])
            top = int(data["top"][i])
            width = int(data["width"][i])
            height = int(data["height"][i])

            blocks[group_key]["left"].append(left)
            blocks[group_key]["top"].append(top)
            blocks[group_key]["right"].append(left + width)
            blocks[group_key]["bottom"].append(top + height)

        # Convert blocks to OCRResult objects
        results = []
        for block_data in blocks.values():
            if not block_data["texts"]:
                continue

            # Combine all text in the block
            combined_text = " ".join(block_data["texts"])

            # Calculate average confidence
            avg_confidence = sum(block_data["confidences"]) / len(
                block_data["confidences"]
            )

            # Calculate bounding box that encompasses all words in the block
            min_x = min(block_data["left"])
            min_y = min(block_data["top"])
            max_x = max(block_data["right"])
            max_y = max(block_data["bottom"])

            width = max_x - min_x
            height = max_y - min_y

            try:
                box = Box(x=min_x, y=min_y, width=width, height=height)
                result = OCRResult(
                    text=combined_text, confidence=avg_confidence, box=box
                )
                results.append(result)
            except ValueError:
                # Skip invalid boxes
                continue

        return results

    def detect_text_paragraphs(self, image: np.ndarray, **kwargs) -> list[OCRResult]:
        """Detect text paragraphs and return results with bounding boxes.

        Convenience method for paragraph-level text detection.

        Args:
            image: Input RGB image as numpy array
            **kwargs: Additional arguments (config, lang, min_confidence)

        Returns:
            list[OCRResult]: List of OCR results with paragraph bounding boxes
        """
        return self.detect_text_blocks(image, level=3, **kwargs)

    def detect_text_lines(self, image: np.ndarray, **kwargs) -> list[OCRResult]:
        """Detect text lines and return results with bounding boxes.

        Convenience method for line-level text detection.

        Args:
            image: Input RGB image as numpy array
            **kwargs: Additional arguments (config, lang, min_confidence)

        Returns:
            list[OCRResult]: List of OCR results with line bounding boxes
        """
        return self.detect_text_blocks(image, level=4, **kwargs)

    def get_backend_info(self) -> dict[str, Any]:
        """Get information about the backend.

        Returns:
            dict: Backend information
        """
        try:
            version = str(pytesseract.get_tesseract_version())
        except Exception:
            version = "Unknown"

        return {
            "name": "Tesseract",
            "version": version,
            "config": self.config,
            "supported_languages": self._get_supported_languages(),
        }

    def _get_supported_languages(self) -> list[str]:
        """Get list of supported languages.

        Returns:
            list[str]: List of supported language codes
        """
        try:
            langs = pytesseract.get_languages(config=self.config.config_string)
            return sorted(langs)
        except Exception:
            return Lang.get_supported_languages()
