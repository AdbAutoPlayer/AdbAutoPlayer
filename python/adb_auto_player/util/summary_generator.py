"""Module responsible for generating and managing summary counts of phrases.

Provides a singleton SummaryGenerator class that keeps track of counts,
prints JSON summaries if a JSON log handler is present, and logs updates.
"""

import sys

from adb_auto_player.ipc import Summary


class SummaryGenerator:
    """Singleton class to maintain and update counts for given phrases.

    Generate summary messages, and optionally print JSON-formatted summaries
    when a JsonLogHandler is present in the logging configuration.

    TODO: Add sections or categories with custom subheader
    TODO: allow ordering
    """

    _instance = None

    def __new__(cls):
        """Create or return the singleton instance of SummaryGenerator.

        Returns:
            The singleton instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize SummaryGenerator.

        _json_handler_present will be set when the JsonLogHandler is initialized.
        """
        self.counters: dict[str, int | str | float] = {}
        self._json_handler_present = False

    @classmethod
    def set_json_handler_present(cls):
        """Called by JsonLogHandler to notify of its presence."""
        instance = cls()  # Get singleton instance
        instance._json_handler_present = True

    @classmethod
    def add_count(cls, phrase: str, count: int = 1) -> None:
        """Increment the count for the specified phrase by the given count.

        If a JsonLogHandler is present, print a JSON summary.

        Args:
            phrase: The phrase to increment the count for.
            count: The amount to increment. Defaults to 1.
        """
        instance = cls()

        value = instance.counters.get(phrase, 0)
        if not isinstance(value, int):
            raise TypeError(f"SummaryGenerator: Value for '{phrase}' is not an int")

        instance.counters[phrase] = value + count
        instance._json_flush()

    @classmethod
    def set(cls, phrase: str, item: int | str | float) -> None:
        """Set the value for the specified phrase.

        If a JsonLogHandler is present, print a JSON summary.

        Args:
            phrase: The phrase to set the value for.
            item: The value to set.
        """
        instance = cls()
        instance.counters[phrase] = item
        instance._json_flush()

    def _json_flush(self) -> None:
        """Print JSON summary if JsonLogHandler is present and summary exists."""
        if self._json_handler_present:
            if message := self.get_summary_message():
                summary = Summary(message)
                print(summary.to_json())
                sys.stdout.flush()

    def get_summary_message(self) -> str | None:
        """Generate a summary message of all phrase counts.

        Returns:
            The formatted summary message or None if no counters exist.
        """
        if not self.counters:
            return None

        lines = [f"{phrase}: {count}" for phrase, count in self.counters.items()]
        summary = "=== SUMMARY ===\n" + "\n".join(lines)
        return summary
