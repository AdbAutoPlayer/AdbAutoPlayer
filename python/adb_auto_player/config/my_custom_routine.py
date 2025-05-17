"""Module for MyCustomRoutineConfig."""

from pydantic import BaseModel, Field


class MyCustomRoutineConfig(BaseModel):
    """My Custom Routine config model."""

    skip_daily_tasks_today: bool = Field(default=False, alias="Skip Daily Tasks Today")
    daily_tasks: list = Field(
        default_factory=list,
        alias="Daily Tasks",
        json_schema_extra={
            "constraint_type": "MyCustomRoutine",
            "default_value": [],
        },
    )
    repeating_tasks: list = Field(
        default_factory=list,
        alias="Repeating Tasks",
        json_schema_extra={
            "constraint_type": "MyCustomRoutine",
            "default_value": [],
        },
    )
