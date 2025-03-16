"""Base configuration functionality for all game configs."""

import tomllib
from pathlib import Path

from adb_auto_player.ipc.constraint import (
    ConstraintType,
    create_checkbox_constraint,
    create_image_checkbox_constraint,
    create_multicheckbox_constraint,
    create_number_constraint,
)
from pydantic import BaseModel


class ConfigBase(BaseModel):
    """Base configuration class with shared functionality."""

    @classmethod
    def from_toml(cls, file_path: Path):
        """Create a Config instance from a TOML file.

        Args:
            file_path (Path): Path to the TOML file.

        Returns:
            An instance of the Config class initialized with data from the TOML file.
        """
        with open(file_path, "rb") as f:
            toml_data = tomllib.load(f)

        return cls(**toml_data)

    @classmethod
    def get_constraints(cls) -> dict[str, dict[str, ConstraintType]]:
        """Get constraints from ADB Auto Player IPC, derived from model schema."""
        schema = cls.model_json_schema()
        constraints: dict[str, dict[str, ConstraintType]] = {}

        # Process each section in the main properties
        for section_name, section_ref in schema.get("properties", {}).items():
            # If it's a reference, look up the actual definition
            if "$ref" in section_ref:
                # Extract the definition name from the reference
                # (e.g., '#/$defs/GeneralConfig' -> 'GeneralConfig')
                def_name = section_ref["$ref"].split("/")[-1]
                section_def = schema.get("$defs", {}).get(def_name, {})

                section_constraints: dict[str, ConstraintType] = {}

                # Process each field in the section definition
                for field_name, field_schema in section_def.get(
                    "properties", {}
                ).items():
                    # Handle custom constraint types
                    constraint_type = field_schema.get("constraint_type")

                    if constraint_type == "multicheckbox":
                        # Get the enum reference and look up values
                        items_ref = field_schema.get("items", {}).get("$ref", "")
                        enum_name = items_ref.split("/")[-1]
                        enum_values = (
                            schema.get("$defs", {}).get(enum_name, {}).get("enum", [])
                        )
                        section_constraints[field_name] = (
                            create_multicheckbox_constraint(enum_values)
                        )

                    elif constraint_type == "image_checkbox":
                        # Get the enum reference and look up values
                        items_ref = field_schema.get("items", {}).get("$ref", "")
                        enum_name = items_ref.split("/")[-1]
                        enum_values = (
                            schema.get("$defs", {}).get(enum_name, {}).get("enum", [])
                        )
                        section_constraints[field_name] = (
                            create_image_checkbox_constraint(enum_values)
                        )

                    # Handle integer fields with constraints
                    elif field_schema.get("type") == "integer":
                        # Get minimum and maximum if they exist
                        minimum = field_schema.get("minimum")
                        maximum = field_schema.get("maximum")
                        section_constraints[field_name] = create_number_constraint(
                            minimum=minimum, maximum=maximum
                        )

                    # Handle boolean fields
                    elif field_schema.get("type") == "boolean":
                        section_constraints[field_name] = create_checkbox_constraint()

                    # Default to number constraint if type is not recognized
                    else:
                        section_constraints[field_name] = create_number_constraint()

                constraints[section_name] = section_constraints

        return constraints
