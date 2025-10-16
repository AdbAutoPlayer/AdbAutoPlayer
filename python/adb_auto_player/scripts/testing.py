from adb_auto_player.device.adb import AdbController
from adb_auto_player.models.geometry import Point

if __name__ == "__main__":
    AdbController().hold(Point(500, 500))
