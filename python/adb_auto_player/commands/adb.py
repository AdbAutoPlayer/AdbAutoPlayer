"""Simple ADB Commands."""

from adb_auto_player.adb import exec_wm_size, wm_size_reset
from adb_auto_player.commands.gui_categories import CommandCategory
from adb_auto_player.decorators.register_command import GuiMetadata, register_command


# This command should probably be game specific in the future if there are any games
# that use a different resolution.
@register_command(
    gui=GuiMetadata(
        label="Set Display Size 1080x1920",
        category=CommandCategory.SETTINGS_PHONE_DEBUG,
    ),
    name="WMSize1080x1920",
)
def _exec_wm_size_1080_1920():
    exec_wm_size(resolution="1080x1920")


@register_command(
    gui=GuiMetadata(
        label="Reset Display Size",
        category=CommandCategory.SETTINGS_PHONE_DEBUG,
    ),
    name="WMSizeReset",
)
def _reset_display_size():
    wm_size_reset()
