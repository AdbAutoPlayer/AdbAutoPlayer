"""CLI."""

import logging
import sys
from functools import lru_cache
from pathlib import Path

from adb_auto_player.cli import ArgparseHelper
from adb_auto_player.file_loader import SettingsLoader
from adb_auto_player.log import setup_logging
from adb_auto_player.task_loader import get_game_tasks
from adb_auto_player.util import DevHelper, Execute


@lru_cache
def find_project_root(marker: str = "AdbAutoPlayer") -> Path:
    """Search upwards from cwd to find the AdbAutoPlayer directory itself.

    Returns:
        Path to the AdbAutoPlayer folder.

    Raises:
        RuntimeError: If the marker cannot be found in any parent directory.
    """
    current = Path.cwd()

    while True:
        candidate = current / marker
        if candidate.is_dir():  # found it
            logging.info(f"Found AdbAutoPlayer directory: {candidate}")
            return candidate  # return the folder itself

        if current == current.parent:  # filesystem root reached
            break
        current = current.parent

    raise RuntimeError(
        "Could not find 'AdbAutoPlayer' directory in the current path "
        "or any of its parents."
    )


def main() -> None:
    """Main entry point of the CLI.

    This function parses the command line arguments, sets up the logging based on
    the output format and log level, and then runs the specified command.
    """
    parser = ArgparseHelper.build_argument_parser(get_game_tasks())
    args = parser.parse_args()

    if not args.command:
        parser.error("the following arguments are required: command")

    setup_logging(args.output, ArgparseHelper.get_log_level_from_args(args))
    DevHelper.log_is_main_up_to_date()

    app_config_dir = args.app_config_dir
    resource_dir = args.resource_dir

    if not app_config_dir:
        logging.warning(
            "--app-config-dir not provided, attempting to resolve automatically..."
        )
        project_root = find_project_root()
        app_config_dir = project_root / "src-tauri" / "settings"
    else:
        app_config_dir = Path(app_config_dir)
    logging.info(f"App Config Dir: {app_config_dir}")

    if not resource_dir:
        logging.warning(
            "--resource-dir not provided, attempting to resolve automatically..."
        )
        project_root = find_project_root()
        resource_dir = project_root / "src-tauri" / "src-python" / "adb_auto_player"
    else:
        resource_dir = Path(resource_dir)
    logging.info(f"Resource Dir: {resource_dir}")

    SettingsLoader.set_app_config_dir(app_config_dir)
    SettingsLoader.set_resource_dir(resource_dir)

    e = Execute.find_command_and_execute(args.command, get_game_tasks())
    if isinstance(e, BaseException):
        logging.error(e, exc_info=True)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
    sys.exit(0)
