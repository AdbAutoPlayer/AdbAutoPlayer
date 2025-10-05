from enum import Enum, auto


class CacheGroup(Enum):
    """LRU Cache Registry Group."""

    GAME_SETTINGS = auto()
    ADB_AUTO_PLAYER_SETTINGS = auto()
    ADB = auto()
