"""GFL2 Game Module."""

import logging

from adb_auto_player import Game
from adb_auto_player.decorators import register_command, register_game
from adb_auto_player.models.decorators import GUIMetadata
from pydantic import BaseModel


@register_game(
    name="GFL2",
)
class GFL2(Game):
    """GFL2 Game Class."""

    def __init__(self) -> None:
        """Initialize GFL2."""
        super().__init__()
        self.supports_portrait = True
        self.package_name_substrings = [
            "com.sunborn.girlsfrontline2",
            "com.mica.gfl2",
        ]

    def get_config(self) -> BaseModel:
        """Get config - placeholder implementation."""
        raise NotImplementedError("Configuration not yet implemented for GFL2")

    def _load_config(self):
        """Load config - placeholder implementation."""
        raise NotImplementedError("Configuration not yet implemented for GFL2")

    @register_command(gui=GUIMetadata(label="Run Dailies"))
    def dailies(self) -> None:
        """Run daily tasks for GFL2.
        
        This is a placeholder function for the GFL2 dailies bot.
        The functionality will be implemented at a later time.
        """
        logging.info("GFL2 Dailies Bot - Placeholder Implementation")
        logging.info("This feature is not yet implemented.")
        logging.info("Please check back for future updates.")