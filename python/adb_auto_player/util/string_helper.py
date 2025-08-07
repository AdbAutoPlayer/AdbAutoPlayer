"""String utility functions and helpers."""

import os
import re
from difflib import SequenceMatcher

from adb_auto_player.models import ConfidenceValue


class StringHelper:
    """String manipulation helper methods."""

    @staticmethod
    def get_filename_without_extension(filename_with_path: str) -> str:
        """Extracts filename without extension from path.

        Args:
            filename_with_path: Filename with path.

        Returns:
            Filename without extension.
        """
        base = os.path.basename(filename_with_path)
        name, _ = os.path.splitext(base)
        return name

    @staticmethod
    def get_game_module(module: str) -> str:
        """Derives the game-specific module from a module path string."""
        module = module.strip()

        if not module:
            raise ValueError("Module path cannot be empty or just whitespace.")

        module_path = module.split(".")
        game_module_min_length = 3
        if len(module_path) < game_module_min_length:
            raise ValueError(
                f"Module path '{module}' is too short. "
                f"Failed to extract module after 'games'"
            )

        if module_path[1] != "games":
            raise ValueError(
                f"Invalid module path '{module}'. Expected 'games' as the second part."
            )

        return module_path[2]

    @staticmethod
    def fuzzy_substring_match(
        text: str,
        pattern: str,
        similarity_threshold: ConfidenceValue = ConfidenceValue("80%"),
    ) -> bool:
        """Check if pattern exists as a fuzzy substring in text.

        Args:
            text: The text to search in (OCR result)
            pattern: The pattern to search for (popup message text)
            similarity_threshold: Minimum similarity ratio

        Returns:
            bool: True if fuzzy match found, False otherwise
        """
        text_lower = text.lower()
        pattern_lower = pattern.lower()

        # If pattern is longer than text, no match possible
        if len(pattern_lower) > len(text_lower):
            return False

        # Check all possible substrings of text with the same length as pattern
        for i in range(len(text_lower) - len(pattern_lower) + 1):
            substring = text_lower[i : i + len(pattern_lower)]
            similarity = SequenceMatcher(None, substring, pattern_lower).ratio()
            if similarity >= similarity_threshold:
                return True

        return False

    @staticmethod
    def snake_to_pascal(s: str):
        """snake_case to PascalCase."""
        return "".join(word.capitalize() for word in s.split("_"))

    @staticmethod
    def sanitize_path(log_message: str) -> str:
        """Replaces the username in file paths with $USER or $env:USERNAME.

        Works with both Windows and Unix-style paths.

        Args:
            log_message (str): The log message containing file paths

        Returns:
            str: The sanitized log message with environment variable placeholders
        """
        home_dir: str = os.path.expanduser("~")

        if "\\" in home_dir:  # Windows path
            username: str = home_dir.split("\\")[-1]
            pattern: str = re.escape(f":\\Users\\{username}")
            replacement = r":\\Users\\$env:USERNAME"
            log_message = re.sub(pattern, replacement, log_message)
            pattern = re.escape(f":\\\\Users\\\\{username}")
            replacement = r":\\\\Users\\\\$env:USERNAME"
            log_message = re.sub(pattern, replacement, log_message)

        else:  # Unix path
            username = home_dir.split("/")[-1]
            pattern = f"/home/{username}"
            replacement = "/home/$USER"
            log_message = re.sub(pattern, replacement, log_message)

        return log_message
