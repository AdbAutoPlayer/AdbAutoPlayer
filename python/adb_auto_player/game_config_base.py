"""Base configuration functionality for all game configs."""

import logging
import tomllib
from pathlib import Path
from typing import cast

from adb_auto_player.ipc.constraint import (
    ConstraintType,
    create_checkbox_constraint,
    create_image_checkbox_constraint,
    create_multicheckbox_constraint,
    create_number_constraint,
    create_text_constraint,
)
from pydantic import BaseModel
from pydantic.fields import FieldInfo


class InvalidIntegerConstraintsError(ValueError):
    """Raise when default value is outside min-max bounds.

    This means you have to set ge and/or le in the Pydantic Field schema.
    """

    pass


class MissingDefaultValueError(ValueError):
    """Raised when a config field is missing a default value."""

    pass


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
        toml_data = {}
        if file_path.exists():
            try:
                with open(file_path, "rb") as f:
                    toml_data = tomllib.load(f)

            except Exception as e:
                logging.error(f"Error reading config file: {e} - Using default values")

        default_data = {}
        for field in cls.model_fields.values():
            field = cast(FieldInfo, field)
            if field.alias not in toml_data:
                field_type = field.annotation
                if hasattr(field_type, "model_fields"):
                    default_data[field.alias] = field_type().model_dump()

        merged_data = {**default_data, **toml_data}
        return cls(**merged_data)

    @classmethod
    def get_constraints(cls) -> dict[str, dict[str, ConstraintType]]:
        """Get constraints from ADB Auto Player IPC, derived from model schema."""
        schema = cls.model_json_schema()
        constraints: dict[str, dict[str, ConstraintType]] = {}

        for section_name, section_ref in schema.get("properties", {}).items():
            section_def = cls._resolve_section_definition(schema, section_ref)
            if section_def:
                constraints[section_name] = cls._extract_constraints_from_section(
                    schema, section_def
                )

        return constraints

    @classmethod
    def _resolve_section_definition(cls, schema: dict, section_ref: dict) -> dict:
        """Resolve the definition of a section if it contains a reference."""
        if "$ref" in section_ref:
            def_name = section_ref["$ref"].split("/")[-1]
            return schema.get("$defs", {}).get(def_name, {})
        return {}

    @classmethod
    def _extract_constraints_from_section(
        cls, schema: dict, section_def: dict
    ) -> dict[str, ConstraintType]:
        """Extract constraints from a section definition."""
        section_constraints: dict[str, ConstraintType] = {}
        for field_name, field_schema in section_def.get("properties", {}).items():
            constraint = cls._determine_constraint(schema, field_schema)
            if constraint:
                section_constraints[field_name] = constraint
        return section_constraints

    @classmethod
    def _determine_constraint(
        cls, schema: dict, field_schema: dict
    ) -> ConstraintType | None:
        """Determine the appropriate constraint for a field based on its schema."""
        constraint_type = field_schema.get("constraint_type")
        if constraint_type:
            return cls._handle_constraint_type(schema, field_schema, constraint_type)

        return cls._handle_standard_field_types(field_schema)

    @classmethod
    def _handle_constraint_type(
        cls, schema: dict, field_schema: dict, constraint_type: str
    ) -> ConstraintType:
        """Handle fields with specific constraint types."""
        items_ref = field_schema.get("items", {}).get("$ref", "")
        enum_name = items_ref.split("/")[-1]
        enum_values = schema.get("$defs", {}).get(enum_name, {}).get("enum", [])
        default_value = field_schema.get("default_value", list())
        match constraint_type:
            case "multicheckbox":
                return create_multicheckbox_constraint(
                    choices=enum_values,
                    default_value=default_value,
                    group_alphabetically=field_schema.get(
                        "group_alphabetically", False
                    ),
                )
            case "imagecheckbox":
                return create_image_checkbox_constraint(
                    choices=enum_values,
                    default_value=default_value,
                    image_dir_path=field_schema.get("image_dir_path", ""),
                )
            case _:
                raise ValueError(f"Unknown constraint_type {constraint_type}")

    @classmethod
    def _handle_standard_field_types(cls, field_schema: dict) -> ConstraintType:
        """Handle standard field types like integer, boolean, and default to text."""
        default_value = field_schema.get("default")

        if default_value is None:
            raise MissingDefaultValueError(
                f"Field '{field_schema.get('title') or field_schema.get('name')}' "
                "is missing a default value."
            )

        match field_schema.get("type"):
            case "integer":
                minimum = field_schema.get("minimum") or 1
                maximum = field_schema.get("maximum") or 999

                if default_value > maximum or default_value < minimum:
                    raise InvalidIntegerConstraintsError(
                        f"Default value {default_value} is outside the expected range "
                        f"{minimum}-{maximum}. Set 'le' and/or 'ge' in the "
                        f"Pydantic Field schema explicitly."
                    )

                if not isinstance(minimum, int):
                    raise TypeError(
                        f"Expected 'minimum' to be an int, "
                        f"but got {type(minimum).__name__}"
                    )

                if not isinstance(maximum, int):
                    raise TypeError(
                        f"Expected 'maximum' to be an int, "
                        f"but got {type(maximum).__name__}"
                    )

                return create_number_constraint(
                    minimum=minimum,
                    maximum=maximum,
                    default_value=cast(int, default_value),
                )
            case "boolean":
                return create_checkbox_constraint(cast(bool, default_value))
            case "array":
                raise ValueError(
                    "array config properties need to define "
                    "json_schema_extra.constraint_type"
                )
            case _:
                return create_text_constraint(cast(str, default_value))
