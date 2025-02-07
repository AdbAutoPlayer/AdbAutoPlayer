# Troubleshooting

## [WARNING] No devices found
![emulator-5554_not_found.png](../images/app/no_devices_found.png)

This is a Warning that does not necessarily need to be fixed. You can try following things:

### Windows
- Start **MuMuPlayer** and check the [Windows Setup Guide](windows-setup.md) if MuMuPlayer is configured correctly and running this should not happen

### macOS
- Start **MuMuPlayer**, then go to **Tools** → **Open ADB**:
  ![Open ADB](../images/macos/mumu_player_pro_open_adb.png)
- Minimize and ignore the terminal window that opens.

---

## [ERROR] Device: <device_id> not found
![device_not_found.png](../images/app/device_not_found.png)

Click Edit Main Config and change the Device ID to one of the listed Devices, the correct one will most likely be `emulator-<number>`
![main_config.png](../images/app/main_config.png)

---

### Success!
Once connected, you'll see:
![Connected Successfully](../images/app/successfully_connected.png)

---

## Starting a Game
- Launch a supported game, and the app interface will adapt accordingly:
  ![Game Interface](../images/app/afk_journey.png)

---

### MacOS
- Ensure **ADB Debugging** is enabled in **MuMuPlayer Pro** as described above.
- If **AdbAutoPlayer** doesn't work, verify:
  - The correct device ID is set in `main_config.toml`.
  - ADB is installed and configured (`adb devices` lists your emulator).
