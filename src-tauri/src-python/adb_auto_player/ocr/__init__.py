"""OCR."""

from ._backend import OCRBackend
from .qwen2vl_backend import QwenVLOCRBackend
from .rapidocr_backend import RapidOCRBackend
from .tesseract_backend import TesseractBackend
from .tesseract_config import TesseractConfig
from .tesseract_lang import Lang
from .tesseract_oem import OEM
from .tesseract_psm import PSM

__all__ = [
    "OEM",
    "PSM",
    "Lang",
    "OCRBackend",
    "QwenVLOCRBackend",
    "RapidOCRBackend",
    "TesseractBackend",
    "TesseractConfig",
]
