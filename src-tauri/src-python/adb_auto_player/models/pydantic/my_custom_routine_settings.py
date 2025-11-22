"""Module for Task Lists."""

from pydantic import BaseModel, Field


class TaskListSettings(BaseModel):
    """Task Lists."""

    display_name: str = Field(default="", alias="Display Name", title="Display Name")
    repeat: bool = Field(
        default=True,
        alias="Repeat",
        title="Repeat",
    )
    tasks: list = Field(
        default_factory=list,
        alias="Task List",
        title="Task List",
        json_schema_extra={
            "formType": "TaskList",
        },
    )
