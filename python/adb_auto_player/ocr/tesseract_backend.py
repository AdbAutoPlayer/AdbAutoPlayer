"""Tesseract OCR backend implementation."""

import os
import platform
from enum import IntEnum
from typing import Any

import numpy as np
import pytesseract
from adb_auto_player.models.geometry.box import Box
from adb_auto_player.models.ocr.ocr_result import OCRResult
from pytesseract import TesseractNotFoundError

from .. import ConfigLoader
from ..models.threshold import Threshold
from .tesseract_config import TesseractConfig
from .tesseract_lang import Lang

_NUM_COLORS_IN_RGB = 3


class GroupingLevel(IntEnum):
    """Text grouping levels for OCR detection."""

    BLOCK = 2
    PARAGRAPH = 3
    LINE = 4


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
        config: TesseractConfig | None = None,
    ) -> str:
        """Extract all text from an image as a single string.

        Args:
            image: Input RGB image as numpy array
            config: Optional TesseractConfig override

        Returns:
            Extracted text
        """
        if not config:
            config = self.config

        text = pytesseract.image_to_string(
            image=image,
            config=config.config_string,
            lang=config.lang_string,
        ).strip()

        return text

    def detect_text(
        self,
        image: np.ndarray,
        config: TesseractConfig | None = None,
        min_confidence: Threshold | None = None,
    ) -> list[OCRResult]:
        """Detect text and return results with bounding boxes.

        Args:
            image: Input RGB image as numpy array
            config: Optional TesseractConfig override
            min_confidence: Minimum confidence threshold, default no Threshold

        Returns:
            List of OCR results with bounding boxes
        """
        if not config:
            config = self.config

        if not min_confidence:
            min_confidence = Threshold(0.0)

        data = pytesseract.image_to_data(
            image,
            config=config.config_string,
            lang=config.lang_string,
            output_type=pytesseract.Output.DICT,
        )

        results = []
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            # Skip empty text and low confidence results
            text = data["text"][i].strip()
            confidence = float(data["conf"][i])

            if not text or confidence < min_confidence.tesseract_format:
                continue

            # Extract bounding box coordinates
            x = int(data["left"][i])
            y = int(data["top"][i])
            width = int(data["width"][i])
            height = int(data["height"][i])

            try:
                box = Box(x=x, y=y, width=width, height=height)
                result = OCRResult(text=text, confidence=confidence / 100.0, box=box)
                results.append(result)

            except ValueError:
                # Skip invalid boxes
                continue

        return results

    def detect_text_blocks(
        self,
        image: np.ndarray,
        config: TesseractConfig | None = None,
        min_confidence: Threshold | None = None,
        level: int = GroupingLevel.BLOCK,
    ) -> list[OCRResult]:
        """Detect text blocks and return results with bounding boxes.

        Args:
            image: Input RGB image as numpy array
            config: Optional TesseractConfig override
            min_confidence: Minimum confidence threshold, default no Threshold
            level: GroupingLevel

        Returns:
            List of OCR results with text block bounding boxes
        """
        if not config:
            config = self.config

        if not min_confidence:
            min_confidence = Threshold(0.0)

        data = pytesseract.image_to_data(
            image,
            config=config.config_string,
            lang=config.lang_string,
            output_type=pytesseract.Output.DICT,
        )

        # Group by the specified level (block_num, par_num, etc.)
        blocks = {}
        n_boxes = len(data["text"])

        for i in range(n_boxes):
            text = data["text"][i].strip()
            confidence = float(data["conf"][i])

            if not text or confidence < min_confidence.tesseract_format:
                continue

            # Create grouping key based on level
            if level == GroupingLevel.BLOCK:
                group_key = (data["page_num"][i], data["block_num"][i])
            elif level == GroupingLevel.PARAGRAPH:
                group_key = (
                    data["page_num"][i],
                    data["block_num"][i],
                    data["par_num"][i],
                )
            elif level == GroupingLevel.LINE:
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
            blocks[group_key]["confidences"].append(confidence / 100.0)

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

    def detect_text_paragraphs(
        self,
        image: np.ndarray,
        config: TesseractConfig | None = None,
        min_confidence: Threshold | None = None,
    ) -> list[OCRResult]:
        """Detect text paragraphs and return results with bounding boxes.

        Args:
            image: Input RGB image as numpy array
            config: Optional TesseractConfig override
            min_confidence: Minimum confidence threshold, default no Threshold

        Returns:
            List of OCR results with paragraph bounding boxes
        """
        return self.detect_text_blocks(
            image,
            config=config,
            min_confidence=min_confidence,
            level=GroupingLevel.PARAGRAPH,
        )

    def detect_text_lines(
        self,
        image: np.ndarray,
        config: TesseractConfig | None = None,
        min_confidence: Threshold | None = None,
    ) -> list[OCRResult]:
        """Detect text lines and return results with bounding boxes.

        Args:
            image: Input RGB image as numpy array
            config: Optional TesseractConfig override
            min_confidence: Minimum confidence threshold, default no Threshold

        Returns:
            List of OCR results with line bounding boxes
        """
        return self.detect_text_blocks(
            image,
            config=config,
            min_confidence=min_confidence,
            level=GroupingLevel.LINE,
        )

    def get_backend_info(self) -> dict[str, Any]:
        """Get information about the backend.

        Returns:
            Backend information dictionary
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
            List of supported language codes
        """
        try:
            langs = pytesseract.get_languages(config=self.config.config_string)
            return sorted(langs)
        except Exception:
            return Lang.get_supported_languages()
