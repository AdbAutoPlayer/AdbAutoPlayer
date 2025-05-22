from enum import StrEnum


class AFKJCategory(StrEnum):
    """Enumeration for action categories used in the GUIs accordion menu."""

    GAME_MODES = "Game Modes"
    EVENTS_AND_OTHER = "Events & Other"
    WIP_PLEASE_TEST = "WIP Please Test"
