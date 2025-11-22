"""Tesseract PSM option."""

from enum import StrEnum


class PSM(StrEnum):
    """Tesseract Page Segmentation Mode enumeration."""

    OSD_ONLY = "0"  # Orientation and script detection
    AUTO_PSM_WITH_OSD = "1"  # Automatic page segmentation with OSD.
    AUTO_PSM_NO_OSD = "2"  # Automatic page segmentation, but no OSD, or OCR.
    DEFAULT = "3"  #  Fully automatic page segmentation, but no OSD.
    SINGLE_COLUMN = "4"  # Assume a single column of text of variable sizes.
    SINGLE_BLOCK_VERT_TEXT = "5"  # Assume a single uniform block of vert aligned text.
    SINGLE_BLOCK = "6"  # Assume a single uniform block of text.
    SINGLE_LINE = "7"  # Treat the image as a single text line.
    SINGLE_WORD = "8"  # Treat the image as a single word.
    CIRCLE_WORD = "9"  # Treat the image as a single word in a circle.
    SINGLE_CHAR = "10"  # Treat the image as a single character.
    SPARSE_TEXT = "11"  # Sparse text. Find as much text as possible.
    SPARSE_TEXT_OSD = "12"  # Sparse text with OSD.
    RAW_LINE = "13"  #  Raw line. Bypasses Tesseract-specific hacks.

    @staticmethod
    def from_value(value: int | str) -> "PSM":
        """Get Enum from PSM int or string."""
        return PSM(str(value))
