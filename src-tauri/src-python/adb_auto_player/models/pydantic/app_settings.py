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
    catppuccin = "catppuccin"
    cerberus = "cerberus"
    crimson = "crimson"
    fennec = "fennec"
    hamlindigo = "hamlindigo"
    legacy = "legacy"
    mint = "mint"
    modern = "modern"
    mona = "mona"
    nosh = "nosh"
    nouveau = "nouveau"
    pine = "pine"
    reign = "reign"
    rocket = "rocket"
    rose = "rose"
    sahara = "sahara"
    seafoam = "seafoam"
    terminus = "terminus"
    vintage = "vintage"
    vox = "vox"
    wintry = "wintry"


class Locale(str, Enum):
    en = "en"
    jp = "jp"
    vn = "vn"


class LoggingSettings(BaseModel):
    """Logging settings model."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "FATAL"] = Field(
        "INFO", title="Logging Level"
    )
    action_log_limit: NonNegativeInt = Field(5, title="Log File Limit")


class UISettings(BaseModel):
    """UI Settings model."""

    theme: Theme = Field(default=Theme.catppuccin, title="Theme")
    locale: Locale = Field(default=Locale.en, title="Locale")
    close_should_minimize: bool = Field(
        False, title="Close button should minimize the window"
    )
    notifications_enabled: bool = Field(False, title="Enable Notifications")


class ProfileSettings(BaseModel):
    """Profile Settings model."""

    profiles: list[str] = Field(default=["Default"], title="Profiles", min_length=1)


class AppSettings(BaseModel):
    """App Settings model."""

    profiles: ProfileSettings = Field(default_factory=ProfileSettings, title="Profiles")
    ui: UISettings = Field(default_factory=UISettings, title="User Interface")
    logging: LoggingSettings = Field(default_factory=LoggingSettings, title="Logging")


if __name__ == "__main__":
    print(json.dumps(AppSettings.model_json_schema()))
