"""OCR."""

from .tesseract_backend import TesseractBackend
from .tesseract_config import TesseractConfig
from .tesseract_lang import Lang
from .tesseract_oem import OEM
from .tesseract_psm import PSM

__all__ = ["OEM", "PSM", "Lang", "TesseractBackend", "TesseractConfig"]
