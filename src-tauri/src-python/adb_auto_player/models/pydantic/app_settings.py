"""Global App Settings.

This model is not actually used in the Python source,
but only used to generate a schema for the Form Generator.
Because schemars for rust uses a different schema version.
"""

import json
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field

NonNegativeInt = Annotated[int, Field(ge=0)]


class Theme(str, Enum):
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


class Locale(str, Enum):
    """Locale Enum."""

    en = "en"
    jp = "jp"
    vn = "vn"


class LoggingSettings(BaseModel):
    """Logging settings model."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "FATAL"] = Field(
        "INFO", title="Logging Level"
    )


class UISettings(BaseModel):
    """UI Settings model."""

    theme: Theme = Field(default=Theme.cerberus, title="Theme")
    locale: Locale = Field(default=Locale.en, title="Locale")
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
            "regex": "^https://discordapp\\.com/api/webhooks/.*",
            "htmlTitle": "Discord Webhook has to start with 'https://discordapp.com/api/webhooks/'",
        },
    )


class ProfileSettings(BaseModel):
    """Profile Settings model."""

    profiles: list[str] = Field(default=["Default"], title="Profiles", min_length=1)


class AdvancedSettings(BaseModel):
    """Advanced Settings model."""

    shutdown_after_tasks: bool = Field(default=False, title="Shutdown after Tasks")


class AppSettings(BaseModel):
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
