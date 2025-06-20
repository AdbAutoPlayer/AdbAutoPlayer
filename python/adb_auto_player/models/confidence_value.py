"""Threshold dataclass for confidence values."""

from dataclasses import dataclass

_FLOAT_COMPARISON_TOLERANCE = 1e-9
_MIN_PERCENTAGE_INT = 0
_MAX_PERCENTAGE_INT = 100


@dataclass
class ConfidenceValue:
    """Represents a confidence value with flexible input formats.

    Used for confidence threshold and results.

    Supports:
    - Percentage strings: "80%", "95%"
    - Normalized floats: 0.8, 0.95 (0.0-1.0)
    - Integer percentages: 80, 95 (0-100)
    - String floats: "0.8" ("0.0"-"1.0"), values outside of range will raise ValueError
    - String integers: "80", "95" ("0"-"100")
    - Boolean: True = 100% and False = 0%

    """

    value: float

    def __init__(self, threshold: str | int | float):
        """Initialize threshold from various input formats.

        Args:
            threshold: Threshold value in various formats

        Raises:
            ValueError: If threshold format is invalid or out of range
        """
        self.value = _parse_threshold(threshold)

    @property
    def percentage(self) -> float:
        """Get threshold as percentage (0.0-100.0).

        Returns:
            Threshold as percentage
        """
        return self.value * 100.0

    @property
    def tesseract_format(self) -> float:
        """Get threshold in Tesseract's expected format (0.0-100.0).

        Returns:
            Threshold in Tesseract format
        """
        return self.percentage

    @property
    def cv2_format(self) -> float:
        """Get threshold as normalized float (0.0-1.0).

        Returns:
            Normalized threshold value
        """
        return self.value

    def __str__(self) -> str:
        """String representation as percentage."""
        return f"ConfidenceValue({self.percentage:.1f}%)"

    def __repr__(self) -> str:
        """Developer-friendly representation."""
        return f"ConfidenceValue({self.percentage:.1f}%)"

    def __float__(self) -> float:
        """Allow direct float conversion."""
        return self.value

    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if isinstance(other, ConfidenceValue):
            return abs(self.value - other.value) < _FLOAT_COMPARISON_TOLERANCE
        elif isinstance(other, int | float):
            # Compare with normalized value
            try:
                other_threshold = ConfidenceValue(other)
                return (
                    abs(self.value - other_threshold.value)
                    < _FLOAT_COMPARISON_TOLERANCE
                )
            except ValueError:
                return False
        return False

    def __lt__(self, other) -> bool:
        """Less than comparison."""
        if isinstance(other, ConfidenceValue):
            return self.value < other.value
        elif isinstance(other, int | float):
            try:
                other_threshold = ConfidenceValue(other)
                return self.value < other_threshold.value
            except ValueError:
                return NotImplemented
        return NotImplemented

    def __le__(self, other) -> bool:
        """Less than or equal comparison."""
        return self == other or self < other

    def __gt__(self, other) -> bool:
        """Greater than comparison."""
        if isinstance(other, ConfidenceValue):
            return self.value > other.value
        elif isinstance(other, int | float):
            try:
                other_threshold = ConfidenceValue(other)
                return self.value > other_threshold.value
            except ValueError:
                return NotImplemented
        return NotImplemented

    def __ge__(self, other) -> bool:
        """Greater than or equal comparison."""
        return self == other or self > other


def _normalize_numeric_value(value: int | float) -> float:
    """Normalize numeric value to 0.0-1.0 range.

    Args:
        value: Numeric threshold value

    Returns:
        Normalized threshold value (0.0-1.0)

    Raises:
        ValueError: If value is out of valid range
    """
    if isinstance(value, float):
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"Float needs to be between 0.0 and 1.0, got {value}")
        return value

    if isinstance(value, bool):
        if value:
            return 1.0
        return 0.0

    if _MIN_PERCENTAGE_INT <= value <= _MAX_PERCENTAGE_INT:
        # Treat as percentage
        return float(value) / 100.0
    else:
        raise ValueError(f"Threshold must be between 0-1 or 0-100, got {value}")


def _parse_threshold(threshold: str | int | float) -> float:
    """Parse threshold from various input formats to normalized float (0.0-1.0).

    Args:
        threshold: Input threshold value

    Returns:
        Normalized threshold value (0.0-1.0)

    Raises:
        ValueError: If threshold format is invalid or out of range
    """
    if isinstance(threshold, str):
        threshold = threshold.strip()

        # Handle percentage strings
        if threshold.endswith("%"):
            try:
                value = threshold[:-1]
                value = value.strip()
                percent_value = float(value)
                if not _MIN_PERCENTAGE_INT <= percent_value <= _MAX_PERCENTAGE_INT:
                    raise ValueError(
                        f"Percentage must be between 0% and 100%, got {threshold}"
                    )
                return percent_value / 100.0
            except ValueError as e:
                if "could not convert string to float" in str(e):
                    raise ValueError(f"Invalid percentage format: {threshold}")
                raise

        # Handle string numbers
        try:
            if "." in threshold:
                num_value = float(threshold)
            else:
                num_value = int(threshold)
            return _normalize_numeric_value(num_value)
        except ValueError:
            raise ValueError(f"Invalid threshold format: {threshold}")

    elif isinstance(threshold, int | float):
        return _normalize_numeric_value(threshold)

    else:
        raise ValueError(f"Unsupported threshold type: {type(threshold)}")
