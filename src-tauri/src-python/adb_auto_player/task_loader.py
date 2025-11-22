from functools import lru_cache

from adb_auto_player import commands, games
from adb_auto_player.models.commands import Command
from adb_auto_player.registries import COMMAND_REGISTRY, GAME_REGISTRY


def _load_modules() -> None:
    """Workaround to make static code analysis recognize the imports are required."""
    _ = games.__all__
    _ = commands.__all__


@lru_cache(maxsize=1)
def get_game_tasks() -> dict[str, list[Command]]:
    cmds: dict[str, list[Command]] = {}
    for module, registered_commands in COMMAND_REGISTRY.items():
        if module in GAME_REGISTRY:
            game_name = GAME_REGISTRY[module].name
        else:
            game_name = "Commands"
        if game_name not in cmds:
            cmds[game_name] = []
        cmds[game_name].extend(registered_commands.values())
    return cmds
