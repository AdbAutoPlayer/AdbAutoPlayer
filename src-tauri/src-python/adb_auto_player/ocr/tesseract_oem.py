"""Tesseract OEM option."""

from enum import StrEnum


class OEM(StrEnum):
    """Tesseract OCR Engine Mode enumeration."""

    LEGACY = "0"  # Legacy engine only.
    LSTM_ONLY = "1"  # Neural nets LSTM engine only.
    LEGACY_LSTM_COMBINED = "2"  # Legacy + LSTM engines.
    DEFAULT = "3"  # Default, based on what is available.

    @staticmethod
    def from_value(value: int | str) -> "OEM":
        """Get Enum from OEM int or string."""
        return OEM(str(value))
