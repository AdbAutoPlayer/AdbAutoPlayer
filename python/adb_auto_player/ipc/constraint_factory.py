"""A factory for creating various types of constraint dictionaries.

This module provides a factory class for creating constraint dictionaries that can be
used to define input constraints in a consistent way. The factory supports multiple
constraint types including numbers, selects, checkboxes, and custom constraints.
"""

from .constraint import (
    CheckboxConstraintDict,
    ImageCheckboxConstraintDict,
    MultiCheckboxConstraintDict,
    MyCustomRoutineConstraintDict,
    NumberConstraintDict,
    SelectConstraintDict,
    TextConstraintDict,
)


class ConstraintFactory:
    """A factory class for creating constraint dictionaries of various types."""

    @staticmethod
    def create_number_constraint(
        default_value: int | float,
        minimum: int | float = 1,
        maximum: int | float = 999,
        step: float = 1.0,
    ) -> NumberConstraintDict:
        """Create a number constraint."""
        return NumberConstraintDict(
            type="number",
            minimum=minimum,
            maximum=maximum,
            step=step,
            default_value=default_value,
        )

    @staticmethod
    def create_select_constraint(
        choices: list[str], default_value: str
    ) -> SelectConstraintDict:
        """Create a select constraint."""
        return SelectConstraintDict(
            type="select",
            choices=choices,
            default_value=default_value,
        )

    @staticmethod
    def create_checkbox_constraint(default_value: bool) -> CheckboxConstraintDict:
        """Create a checkbox constraint."""
        return CheckboxConstraintDict(
            type="checkbox",
            default_value=default_value,
        )

    @staticmethod
    def create_multicheckbox_constraint(
        choices: list[str],
        default_value: list[str],
        group_alphabetically: bool,
    ) -> MultiCheckboxConstraintDict:
        """Create a multicheckbox constraint."""
        return MultiCheckboxConstraintDict(
            type="multicheckbox",
            choices=choices,
            default_value=default_value,
            group_alphabetically=group_alphabetically,
        )

    @staticmethod
    def create_image_checkbox_constraint(
        choices: list[str],
        default_value: list[str],
        image_dir_path: str,
    ) -> ImageCheckboxConstraintDict:
        """Create an image checkbox constraint."""
        return ImageCheckboxConstraintDict(
            type="imagecheckbox",
            choices=choices,
            default_value=default_value,
            image_dir_path=image_dir_path,
        )

    @staticmethod
    def create_my_custom_routine_constraint(
        choices: list[str],
    ) -> MyCustomRoutineConstraintDict:
        """Create a My Custom Routine constraint."""
        return MyCustomRoutineConstraintDict(
            type="MyCustomRoutine",
            default_value=[],
            choices=choices,
        )

    @staticmethod
    def create_text_constraint(
        default_value: str, regex: str, title: str
    ) -> TextConstraintDict:
        """Create a text constraint."""
        return TextConstraintDict(
            type="text", regex=regex, title=title, default_value=default_value
        )
