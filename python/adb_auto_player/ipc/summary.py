"""IPC Summary."""

import json


class Summary:
    """Summary message class."""

    def __init__(self, summary_message: str) -> None:
        """Initialize Summary.

        Args:
            summary_message: The summary or progress message.
        """
        self.summary_message = summary_message

    def to_dict(self) -> dict:
        """Convert Summary to dictionary for JSON serialization."""
        return {
            "summary_message": self.summary_message,
        }

    def to_json(self) -> str:
        """Convert Summary JSON."""
        return json.dumps(self.to_dict())
