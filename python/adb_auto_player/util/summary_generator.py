"""Module responsible for generating and managing summary counts of phrases."""

import sys

from adb_auto_player.ipc import Summary

_ValueType = int | str | float


class SummaryGenerator:
    """Singleton class to maintain and update counts for given phrases."""

    _instance = None

    def __new__(cls):
        """Create or return the singleton instance of SummaryGenerator.

        Returns:
            The singleton instance of SummaryGenerator.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init__()  # Explicit initialization
        return cls._instance

    def __init__(self) -> None:
        """Initialize SummaryGenerator.

        _json_handler_present will be set when the JsonLogHandler is initialized.
        """
        if not hasattr(self, "entries"):
            self.entries: dict[str, dict[str, _ValueType]] = {}
            self._json_handler_present = False

    @classmethod
    def set_json_handler_present(cls):
        """Called by JsonLogHandler to notify of its presence."""
        instance = cls()
        instance._json_handler_present = True

    @classmethod
    def increment(cls, section_header: str, item: str, count: int = 1) -> None:
        """Increment the count for a specific item within a section.

        Args:
            section_header: The header under which the item belongs
            item: The specific item to increment
            count: The amount to increment by (default: 1)

        Raises:
            TypeError: If the existing value is not an integer
        """
        instance = cls()

        if section_header not in instance.entries:
            instance.entries[section_header] = {}

        value = instance.entries[section_header].get(item, 0)
        if not isinstance(value, int):
            raise TypeError(
                f"Can't increment non-integer value for '{item}' "
                f"under '{section_header}'. "
                f"Current value: {value} (type: {type(value).__name__})"
            )
        instance.entries[section_header][item] = value + count
        instance._json_flush()

    @classmethod
    def set(cls, section_header: str, item: str, value: _ValueType) -> None:
        """Set a value for a specific item within a section.

        Args:
            section_header: The header under which the item belongs
            item: The specific item to set
            value: The value to set (can be int, str, or float)
        """
        instance = cls()

        if section_header not in instance.entries:
            instance.entries[section_header] = {}

        instance.entries[section_header][item] = value
        instance._json_flush()

    def _json_flush(self) -> None:
        if self._json_handler_present and (message := self.get_summary_message()):
            print(Summary(message).to_json())
            sys.stdout.flush()

    def get_summary_message(self) -> str | None:
        """Generate a formatted summary message from the current entries.

        Returns:
            str: Formatted summary message with sections and items
            None: If no entries exist
        """
        if not self.entries:
            return None

        lines = ["=== SUMMARY ==="]
        for i, (header, phrases) in enumerate(self.entries.items()):
            lines.append(header)
            for phrase, count in phrases.items():
                lines.append(f"  {phrase}: {count}")
            if i < len(self.entries) - 1:
                lines.append("")

        return "\n".join(lines)
