import inspect

import adb_auto_player.adb as adb
import eel
import adb_auto_player.plugin_loader as plugin_loader

main_config = plugin_loader.get_main_config()
device = None


def init() -> None:
    """This is only so functions here can be exposed."""
    return None


@eel.expose
def get_running_app() -> str:
    global device
    if device is None:
        device = adb.get_device(main_config)
    return adb.get_currently_running_app(device)


@eel.expose
def test_bla_bla() -> None:
    global device
    if device is None:
        device = adb.get_device(main_config)
    module = plugin_loader.load_plugin_module("AFKJourney")
    classes = [cls for name, cls in inspect.getmembers(module, inspect.isclass)]
    class_name = classes[0]
    obj = class_name(device, main_config)
    print(device, main_config)
    obj.push_afk_stages(season=True)
    print(obj)
