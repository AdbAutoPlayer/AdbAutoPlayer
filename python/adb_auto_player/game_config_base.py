"""Base configuration functionality for all game configs."""

import tomllib
from pathlib import Path

from adb_auto_player.ipc.constraint import (
    ConstraintType,
    create_checkbox_constraint,
    create_image_checkbox_constraint,
    create_multicheckbox_constraint,
    create_number_constraint,
    create_text_constraint,
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

        match constraint_type:
            case "multicheckbox":
                return create_multicheckbox_constraint(enum_values)
            case "image_checkbox":
                return create_image_checkbox_constraint(enum_values)
            case _:
                raise ValueError(f"Unknown constraint_type {constraint_type}")

    @classmethod
    def _handle_standard_field_types(cls, field_schema: dict) -> ConstraintType:
        """Handle standard field types like integer, boolean, and default to text."""
        match field_schema.get("type"):
            case "integer":
                minimum = field_schema.get("minimum") or 1
                maximum = field_schema.get("maximum") or 999
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
                )
            case "boolean":
                return create_checkbox_constraint()
            case _:
                return create_text_constraint()
