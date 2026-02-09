import logging
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class TomlSettings(BaseModel):
    """Base Settings class with shared functionality."""

    @classmethod
    def from_toml(cls, file_path: Path):
        """Create a TomlSettings instance from a TOML file.

        Args:
            file_path (Path): Path to the TOML file.

        Returns:
            An instance of TomlSettings class initialized with data from the TOML file.
        """
        settings = cls()

        if not file_path.exists():
            logging.debug("Using default Settings")
            return settings

        try:
            with open(file_path, "rb") as f:
                toml_data = tomllib.load(f)

            settings = cls.model_validate(
                {**settings.model_dump(by_alias=True), **toml_data},
                extra="ignore",
                by_alias=True,
                by_name=True,
            )
        except Exception as e:
            logging.error(f"Error reading Settings: {e} - using default")

        return settings

    def generate_model_json_schema_with_task_list_choices(
        self, choices: list[str]
    ) -> dict[str, Any]:
        """Generate the JSON schema for the model with dynamic Task List enum choices.

        This method produces the standard `model_json_schema()` of the Pydantic model,
        but injects a dynamic `TaskListEnum` definition into the schema and updates
        the `"Task List"` property in `TaskListSettings` to reference this enum.

        Args:
            choices (list[str]): The list of allowed values for the Task List items.

        Returns:
            dict[str, Any]: A JSON Schema dict with the `TaskListEnum` choices applied.
        """
        schema = self.model_json_schema()
        defs = schema.setdefault("$defs", {})
        if "TaskListSettings" in defs and "properties" in defs["TaskListSettings"]:
            defs["TaskListSettings"]["properties"]["Task List"]["items"] = {
                "$ref": "#/$defs/TaskListEnum"
            }

            defs["TaskListEnum"] = {
                "title": "TaskListEnum",
                "type": "string",
                "enum": choices,
            }
        return schema
