"""Module responsible for generating and managing summary counts of phrases.

Provides a singleton SummaryGenerator class that keeps track of counts,
prints JSON summaries if a JSON log handler is present, and logs updates.
"""

import logging
import sys

from adb_auto_player.ipc.summary import Summary
from adb_auto_player.logging_setup import JsonLogHandler


def _is_using_json_handler() -> bool:
    """Check if the root logger has a JsonLogHandler among its handlers.

    Returns:
        True if a JsonLogHandler is present, False otherwise.
    """
    logger = logging.getLogger()
    return any(isinstance(handler, JsonLogHandler) for handler in logger.handlers)


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
            cls._instance._init()
        return cls._instance

    def _init(self):
        """Initialize the instance variables."""
        self.counters = {}
        self._json_handler_present = _is_using_json_handler()

    @staticmethod
    def add_count(phrase: str, count: int = 1) -> None:
        """Increment the count for the specified phrase by the given count.

        If a JsonLogHandler is present, print a JSON summary.

        Args:
            phrase: The phrase to increment the count for.
            count: The amount to increment. Defaults to 1.
        """
        generator = SummaryGenerator()

        if phrase not in generator.counters:
            generator.counters[phrase] = 0
        generator.counters[phrase] += count

        generator._json_flush()

    @staticmethod
    def set(phrase: str, item: int | str | float) -> None:
        """Set the value for the specified phrase.

        If a JsonLogHandler is present, print a JSON summary.

        Args:
            phrase: The phrase to set the value for.
            item: The value to set.
        """
        generator = SummaryGenerator()
        generator.counters[phrase] = item
        generator._json_flush()

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
