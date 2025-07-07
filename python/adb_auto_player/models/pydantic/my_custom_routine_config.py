"""Module for MyCustomRoutineConfig."""

from pydantic import BaseModel, Field


class MyCustomRoutineConfig(BaseModel):
    """My Custom Routine config model."""

    display_name: str = Field(default="", alias="Display Name")
    repeat: bool = Field(
        default=True,
        alias="Repeat",
    )
    tasks: list = Field(
        default_factory=list,
        alias="Task List",
        json_schema_extra={
            "constraint_type": "MyCustomRoutine",
            "default_value": [],
        },
    )
