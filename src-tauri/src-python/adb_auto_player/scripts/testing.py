from adb_auto_player.device.adb import XiaomiInput

if __name__ == "__main__":
    XiaomiInput().key_press(XiaomiInput.keycode("W"), 5)
