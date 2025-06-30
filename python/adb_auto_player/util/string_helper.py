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
