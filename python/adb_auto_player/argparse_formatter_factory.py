"""Argparse Formatter Factory."""

import argparse

from adb_auto_player import Command


def build_argparse_formatter(commands_by_category: dict[str, list[Command]]):
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
                        tooltip = getattr(cmd.menu_option, "tooltip", "")
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
                            tooltip = getattr(cmd.menu_option, "tooltip", "")
                            if tooltip:
                                parts.append(f"    {cmd.name:<30} {tooltip}")
                            else:
                                parts.append(f"    {cmd.name}")

                return "\n".join(parts) + "\n"

            return super()._format_action(action)

    return CustomArgparseFormatter
