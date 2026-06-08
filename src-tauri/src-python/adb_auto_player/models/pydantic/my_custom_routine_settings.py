"""Module for Task Lists."""

from pydantic import BaseModel, Field, field_validator


class TaskItem(BaseModel):
    """A single task entry in a custom routine."""

    name: str = Field(alias="name", title="name")
    repeat: bool = Field(default=True, alias="repeat", title="repeat")

    @classmethod
    def from_name(cls, name: str) -> "TaskItem":
        """Create a TaskItem from a plain task name string."""
        return cls(name=name)


class TaskListSettings(BaseModel):
    """Task Lists."""

    display_name: str = Field(default="", alias="Display Name", title="Display Name")
    repeat: bool = Field(
        default=True,
        alias="Repeat",
        title="Repeat",
    )
    tasks: list[TaskItem] = Field(
        default_factory=list,
        alias="Task List",
        title="Task List",
        json_schema_extra={
            "formType": "TaskList",
        },
    )

    @field_validator("tasks", mode="before")
    @classmethod
    def coerce_tasks(cls, v: list) -> list:
        """Accept both plain strings (legacy) and TaskItem dicts/objects."""
        result = []
        for item in v:
            if isinstance(item, str):
                result.append({"name": item, "repeat": True})
            else:
                result.append(item)
        return result
