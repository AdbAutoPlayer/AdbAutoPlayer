"""String utility functions and helpers."""

import os


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
