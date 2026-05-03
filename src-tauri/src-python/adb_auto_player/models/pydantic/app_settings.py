"""Global App Settings.

This model is not actually used in the Python source,
but only used to generate a schema for the Form Generator.
Because schemars for rust uses a different schema version.
"""

import json
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from .toml_settings import TomlSettings

NonNegativeInt = Annotated[int, Field(ge=0)]


class Theme(StrEnum):
    """Theme Enum."""

    catppuccin = "catppuccin"
    cerberus = "cerberus"
    crimson = "crimson"
    fennec = "fennec"
    modern = "modern"
    mona = "mona"
    nosh = "nosh"
    nouveau = "nouveau"
    pine = "pine"
    rose = "rose"
    seafoam = "seafoam"
    terminus = "terminus"
    vintage = "vintage"
    vox = "vox"
    wintry = "wintry"


class Locale(StrEnum):
    """Locale Enum."""

    en = "en"
    jp = "jp"
    vn = "vn"


class LogPanelPosition(StrEnum):
    """Log Panel Position Enum."""

    right = "right"
    bottom = "bottom"


class LoggingSettings(BaseModel):
    """Logging settings model."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "FATAL"] = Field(
        "INFO", title="Logging Level"
    )


class UISettings(BaseModel):
    """UI Settings model."""

    theme: Theme = Field(default=Theme.cerberus, title="Theme")
    locale: Locale = Field(default=Locale.en, title="Locale")
    log_panel_position: LogPanelPosition = Field(
        default=LogPanelPosition.right, title="Log Panel Position"
    )
    close_should_minimize: bool = Field(
        False, title="Close button should minimize the window"
    )


class NotificationSettings(BaseModel):
    """Notification Settings model."""

    desktop_notifications: bool = Field(False, title="Desktop Notifications")
    discord_webhook: str = Field(
        "",
        title="Discord Webhook",
        json_schema_extra={
            "regex": "^https://(discord|discordapp)\\.com/api/webhooks/.*",
            "htmlTitle": (
                "Discord Webhook has to start with 'https://discord.com/api/webhooks/' "
                "or 'https://discordapp.com/api/webhooks/'"
            ),
        },
    )


class ProfileSettings(BaseModel):
    """Profile Settings model."""

    profiles: list[str] = Field(default=["Default"], title="Profiles", min_length=1)
    active_profile: int = Field(default=0, title="Active Profile")


class AdvancedSettings(BaseModel):
    """Advanced Settings model."""

    shutdown_after_tasks: bool = Field(default=False, title="Shutdown after Tasks")
    restart_stuck_task: bool = Field(
        default=False, title="Watchdogs: Restart Game if Task is Stuck"
    )
    restart_stuck_task_after_mins: int = Field(
        default=60, ge=3, title="Watchdogs: Restart After (Minutes)"
    )
    action_delay: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        title="Action Delay (Seconds)",
        description="Wait time after a standard click or action.",
    )
    navigation_delay: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        title="Navigation Delay (Seconds)",
        description="Wait time after a screen transition or navigation action.",
    )
    template_timeout: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        title="Template Timeout (Seconds)",
        description="Max time to wait for an image/template to appear.",
    )
    watchdog_restart_delay: int = Field(
        default=40,
        ge=10,
        le=300,
        title="Watchdog Restart Delay (Seconds)",
        description="Wait time before restarting the task if the game is closed.",
    )


class AppSettings(TomlSettings):
    """App Settings model."""

    profiles: ProfileSettings = Field(default_factory=ProfileSettings, title="Profiles")
    ui: UISettings = Field(default_factory=UISettings, title="User Interface")
    notifications: NotificationSettings = Field(
        default_factory=NotificationSettings, title="Notifications"
    )
    logging: LoggingSettings = Field(default_factory=LoggingSettings, title="Logging")
    advanced: AdvancedSettings = Field(
        default_factory=AdvancedSettings, title="Advanced"
    )


if __name__ == "__main__":
    print(json.dumps(AppSettings.model_json_schema()))
