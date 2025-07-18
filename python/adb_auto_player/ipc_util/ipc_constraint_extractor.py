"""Constraint extraction functionality for Pydantic models."""

from typing import cast

from adb_auto_player.exceptions import (
    InvalidBoundaryError,
    InvalidDefaultValueError,
    MissingBoundaryValueError,
    MissingDefaultValueError,
    RegexMissingTitleError,
)
from adb_auto_player.ipc import (
    ConstraintFactory,
    ConstraintType,
    NumberConstraintDict,
)
from adb_auto_player.models.commands import Command
from adb_auto_player.registries import CUSTOM_ROUTINE_REGISTRY
from adb_auto_player.util import StringHelper
from pydantic import BaseModel


class IPCConstraintExtractor:
    """Utility class for extracting constraints from Pydantic model schemas."""

    @staticmethod
    def get_constraints_from_model(
        model_class: type["BaseModel"],
        commands: list[Command] | None = None,
    ) -> dict[str, dict[str, ConstraintType]]:
        """Get constraints from a Pydantic model schema."""
        schema = model_class.model_json_schema()
        constraints: dict[str, dict[str, ConstraintType]] = {}

        for section_name, section_ref in schema.get("properties", {}).items():
            section_def = IPCConstraintExtractor._resolve_section_definition(
                schema, section_ref
            )
            if section_def:
                constraints[section_name] = (
                    IPCConstraintExtractor._extract_constraints_from_section(
                        schema,
                        section_def,
                        model_class.__module__,
                        commands=commands,
                    )
                )

        return constraints

    @staticmethod
    def _resolve_section_definition(schema: dict, section_ref: dict) -> dict:
        """Resolve the definition of a section if it contains a reference."""
        if "$ref" in section_ref:
            def_name = section_ref["$ref"].split("/")[-1]
            return schema.get("$defs", {}).get(def_name, {})
        return {}

    @staticmethod
    def _extract_constraints_from_section(
        schema: dict,
        section_def: dict,
        model_module: str,
        commands: list[Command] | None = None,
    ) -> dict[str, ConstraintType]:
        """Extract constraints from a section definition."""
        section_constraints: dict[str, ConstraintType] = {}
        for field_name, field_schema in section_def.get("properties", {}).items():
            constraint = IPCConstraintExtractor._determine_constraint(
                schema,
                field_schema,
                model_module,
                commands=commands,
            )
            if constraint:
                section_constraints[field_name] = constraint
        return section_constraints

    @staticmethod
    def _determine_constraint(
        schema: dict,
        field_schema: dict,
        model_module: str,
        commands: list[Command] | None = None,
    ) -> ConstraintType | None:
        """Determine the appropriate constraint for a field based on its schema."""
        constraint_type = field_schema.get("constraint_type")
        if constraint_type:
            return IPCConstraintExtractor._handle_constraint_type(
                schema,
                field_schema,
                constraint_type,
                model_module,
                commands=commands,
            )

        return IPCConstraintExtractor._handle_standard_field_types(field_schema)

    @staticmethod
    def _handle_constraint_type(
        schema: dict,
        field_schema: dict,
        constraint_type: str,
        model_module: str,
        commands: list[Command] | None = None,
    ) -> ConstraintType:
        """Handle fields with specific constraint types."""
        items_ref = field_schema.get("items", {}).get("$ref", "")
        enum_name = items_ref.split("/")[-1]
        enum_values = schema.get("$defs", {}).get(enum_name, {}).get("enum", [])
        default_value = field_schema.get("default_value", list())

        match constraint_type:
            case "multicheckbox":
                return ConstraintFactory.create_multicheckbox_constraint(
                    choices=enum_values,
                    default_value=default_value,
                    group_alphabetically=field_schema.get(
                        "group_alphabetically", False
                    ),
                )
            case "imagecheckbox":
                return ConstraintFactory.create_image_checkbox_constraint(
                    choices=enum_values,
                    default_value=default_value,
                    image_dir_path=field_schema.get("image_dir_path", ""),
                )
            case "MyCustomRoutine":
                module = StringHelper.get_game_module(model_module)
                choices = list(CUSTOM_ROUTINE_REGISTRY.get(module, {}).keys())
                if not choices:
                    raise ValueError("MyCustomRoutine constraint requires menu options")
                return ConstraintFactory.create_my_custom_routine_constraint(
                    choices=choices
                )
            case _:
                raise ValueError(f"Unknown constraint_type {constraint_type}")

    @staticmethod
    def _handle_standard_field_types(field_schema: dict) -> ConstraintType:
        """Handle standard field types like integer, boolean, and default to text."""
        default_value = field_schema.get("default")
        field_name = field_schema.get("title") or field_schema.get("name")

        if default_value is None:
            raise MissingDefaultValueError(
                f"Field '{field_name}' is missing a default value."
            )

        field_type = field_schema.get("type")
        match field_type:
            case "integer" | "number":
                if field_type == "integer":
                    return _get_integer_constraint(field_schema)
                return _get_number_constraint(field_schema)
            case "boolean":
                return ConstraintFactory.create_checkbox_constraint(
                    cast(bool, default_value)
                )
            case "array":
                raise ValueError(
                    "array config properties need to define "
                    "json_schema_extra.constraint_type"
                )
            case "string":
                regex = field_schema.get("regex", "")
                title = field_schema.get("title", "")
                if regex != "" and title == "":
                    raise RegexMissingTitleError(
                        "Regex should not be used without title. "
                        "Title is displayed when the input is invalid. "
                        "https://www.w3schools.com/tags/att_title.asp"
                    )

                return ConstraintFactory.create_text_constraint(
                    default_value=cast(str, default_value),
                    regex=regex,
                    title=title,
                )
            case _:
                raise NotImplementedError(
                    f"Field Schema Type '{field_type}' not implemented."
                )


def _get_number_constraint(field_schema: dict) -> NumberConstraintDict:
    """Returns number constraint."""
    field_name = field_schema.get("title") or field_schema.get("name")
    default_value = field_schema.get("default")

    if not isinstance(default_value, int | float):
        raise InvalidDefaultValueError(
            f"Field '{field_name}' default_value should be an int or float."
        )

    minimum = field_schema.get("minimum")
    maximum = field_schema.get("maximum")

    if minimum is None or maximum is None:
        raise MissingBoundaryValueError(
            f"Field '{field_name}' is missing boundaries. "
            f"Set 'le' or 'lt and 'ge' or 'gt' in the "
            f"Pydantic Field schema explicitly."
        )

    if not isinstance(minimum, int | float):
        raise TypeError(
            f"Expected 'minimum' to be an int or float, but got "
            f"{type(minimum).__name__}"
        )

    if not isinstance(maximum, int | float):
        raise TypeError(
            f"Expected 'maximum' to be an int or float, "
            f"but got {type(maximum).__name__}"
        )

    if default_value > maximum or default_value < minimum:
        raise InvalidBoundaryError(
            f"Field '{field_name}' "
            f"Default value {default_value} is outside the expected range "
            f"{minimum}-{maximum}. Set 'le' or 'lt and 'ge' or 'gt' in the "
            f"Pydantic Field schema explicitly."
        )

    return ConstraintFactory.create_number_constraint(
        minimum=minimum,
        maximum=maximum,
        default_value=cast(float, default_value),
        step=field_schema.get("step", 1.0),
    )


def _get_integer_constraint(field_schema: dict) -> NumberConstraintDict:
    """Returns integer number constraint."""
    field_name = field_schema.get("title") or field_schema.get("name")
    default_value = field_schema.get("default")

    if not isinstance(default_value, int):
        raise InvalidDefaultValueError(
            f"Field '{field_name}' default_value should be an int."
        )

    minimum = field_schema.get("minimum")
    maximum = field_schema.get("maximum")

    if minimum is None or maximum is None:
        raise MissingBoundaryValueError(
            f"Field '{field_name}' is missing boundaries. "
            f"Set 'le' or 'lt and 'ge' or 'gt' in the "
            f"Pydantic Field schema explicitly."
        )

    if not isinstance(minimum, int):
        raise TypeError(
            f"Expected 'minimum' to be an int, but got {type(minimum).__name__}"
        )

    if not isinstance(maximum, int):
        raise TypeError(
            f"Expected 'maximum' to be an int, but got {type(maximum).__name__}"
        )

    if default_value > maximum or default_value < minimum:
        raise InvalidBoundaryError(
            f"Field '{field_name}' "
            f"Default value {default_value} is outside the expected range "
            f"{minimum}-{maximum}. Set 'le' or 'lt and 'ge' or 'gt' in the "
            f"Pydantic Field schema explicitly."
        )

    return ConstraintFactory.create_number_constraint(
        minimum=minimum,
        maximum=maximum,
        default_value=cast(int, default_value),
        step=field_schema.get("step", 1.0),
    )
