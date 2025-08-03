"""Anything Argparse related."""

import argparse
from argparse import Namespace

from adb_auto_player.models.commands import Command


class ArgparseHelper:
    """Argparse helper functions."""

    @staticmethod
    def build_argument_parser(
        commands: dict[str, list[Command]], exit_on_error: bool = True
    ) -> argparse.ArgumentParser:
        """Builds argparse.ArgumentParser."""
        parser = argparse.ArgumentParser(
            formatter_class=_build_argparse_formatter(commands),
            exit_on_error=exit_on_error,
        )
        parser.add_argument(
            "command",
            help="Command to run",
            nargs="?",  # Make command optional for --server mode
            choices=[
                cmd.name
                for category_commands in commands.values()
                for cmd in category_commands
            ],
        )
        parser.add_argument(
            "--output",
            choices=["terminal", "text", "raw"],
            default="terminal",
            help="Output format",
        )
        parser.add_argument(
            "--log-level",
            choices=["DISABLE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            default="DEBUG",
            help="Log level",
        )
        parser.add_argument(
            "--server",
            action="store_true",
            help="Run in server mode for GUI communication",
        )

        return parser

    @staticmethod
    def get_log_level_from_args(args: Namespace) -> int | str:
        """Get log level from command line arguments."""
        log_level = args.log_level
        if log_level == "DISABLE":
            log_level = 99
        return log_level


def _build_argparse_formatter(commands_by_category: dict[str, list[Command]]):
    """Builds argparse.HelpFormatter."""

    class CustomArgparseFormatter(argparse.HelpFormatter):
        def _format_usage(self, usage, actions, groups, prefix):
            prog = self._prog

            optional_actions = [
                action
                for action in actions
                if action.option_strings and action.dest != "help"
            ]
            optional_str = " ".join(
                f"[{
                    action.option_strings[0]
                    if len(action.option_strings) == 1
                    else action.option_strings[-1]
                }]"
                for action in optional_actions
            )
            command_action = next(
                (
                    action
                    for action in actions
                    if not action.option_strings and action.dest == "command"
                ),
                None,
            )

            if command_action:
                # Get command choices
                choices = (
                    sorted(command_action.choices) if command_action.choices else []
                )
                if len(choices) > (max_choices := 3):
                    command_str = "{" + ", ".join(choices[:max_choices]) + ", ...}"
                else:
                    command_str = "{" + ", ".join(choices) + "}"
            else:
                command_str = ""

            # Format according to argparse's style
            usage_str = f"{prog} [-h] {optional_str} {command_str}"

            return f"{usage_str}\n\n"

        def _format_action(self, action):
            if action.dest == "command":
                parts = []

                common_cmds = commands_by_category.get("Commands", [])
                if common_cmds:
                    parts.append("  Common Commands:")
                    for cmd in sorted(common_cmds, key=lambda c: c.name.lower()):
                        tooltip = getattr(cmd.menu_item, "tooltip", "")
                        if tooltip:
                            parts.append(f"    {cmd.name:<30} {tooltip}")
                        else:
                            parts.append(f"    {cmd.name}")

                other_groups = {
                    k: v for k, v in commands_by_category.items() if k != "Commands"
                }
                if other_groups:
                    parts.append("\n  Game Commands:")
                    for group_name, group_cmds in sorted(
                        other_groups.items(), key=lambda item: item[0].lower()
                    ):
                        parts.append(f"  - {group_name}:")
                        for cmd in sorted(group_cmds, key=lambda c: c.name.lower()):
                            tooltip = getattr(cmd.menu_item, "tooltip", "")
                            if tooltip:
                                parts.append(f"    {cmd.name:<30} {tooltip}")
                            else:
                                parts.append(f"    {cmd.name}")

                return "\n".join(parts) + "\n"

            return super()._format_action(action)

    return CustomArgparseFormatter
