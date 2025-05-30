"""Module responsible for generating and managing summary counts of phrases.

Provides a singleton SummaryGenerator class that keeps track of counts,
prints JSON summaries if a JSON log handler is present, and logs updates.
"""

import logging

from adb_auto_player.ipc.summary import Summary
from adb_auto_player.logging_setup import JsonLogHandler


def _check_json_handler() -> bool:
    """Check if the root logger has a JsonLogHandler among its handlers.

    Returns:
        bool: True if a JsonLogHandler is present, False otherwise.
    """
    logger = logging.getLogger()
    return any(isinstance(handler, JsonLogHandler) for handler in logger.handlers)


class SummaryGenerator:
    """Singleton class to maintain and update counts for given phrases.

    Generate summary messages, and optionally print JSON-formatted summaries
    when a JsonLogHandler is present in the logging configuration.
    """

    _instance = None

    def __new__(cls):
        """Create or return the singleton instance of SummaryGenerator.

        Returns:
            SummaryGenerator: The singleton instance.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        """Initialize the instance variables."""
        self.counters = {}
        self._json_handler_present = _check_json_handler()

    def add_count(self, phrase: str, count: int = 1) -> None:
        """Increment the count for the specified phrase by the given count.

        If a JsonLogHandler is present, print a JSON summary.

        Args:
            phrase (str): The phrase to increment the count for.
            count (int, optional): The amount to increment. Defaults to 1.
        """
        if phrase not in self.counters:
            self.counters[phrase] = 0
        self.counters[phrase] += count
        if self._json_handler_present:
            summary = Summary(self.get_summary_message())
            print(summary.to_json())

    def add_count_and_log(self, phrase: str, count: int = 1) -> None:
        """Increment the count for the specified phrase and log the updated count.

        Args:
            phrase (str): The phrase to increment the count for.
            count (int, optional): The amount to increment. Defaults to 1.
        """
        self.add_count(phrase, count)
        logging.info(f"{phrase}: {self.counters.get(phrase, 0)}")

    def get_summary_message(self) -> str:
        """Generate a summary message of all phrase counts.

        Returns:
            str: The formatted summary message or a no-progress message if empty.
        """
        if not self.counters:
            return "Summary - No progress recorded."

        lines = [f"{phrase}: {count}" for phrase, count in self.counters.items()]
        summary = "=== Summary ===\n" + "\n".join(lines)
        return summary
