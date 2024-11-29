# macOS Setup

This guide provides instructions to set up **AdbAutoPlayer** on macOS Apple Silicon using **MuMuPlayer Pro** as the emulator.

---

## Installation

1. **Download the Tool**  
   - Get the latest release of **AdbAutoPlayer**:  
     [AdbAutoPlayer_MacOS.zip](https://github.com/yulesxoxo/AdbAutoPlayer/releases/latest).  
   - Extract the contents of the `.zip` file to a folder on your computer.

2. **Install MuMuPlayer Pro**  
   - Download and install **MuMuPlayer Pro**: [MuMuPlayer for macOS](https://www.mumuplayer.com/mac/).

3. **Install Homebrew**  
   - Follow the instructions at [brew.sh](https://brew.sh/) to install **Homebrew** (a package manager for macOS).

4. **Install ADB via Homebrew**  
   - Use Homebrew to install the Android Debug Bridge (ADB):  
     ```shell
     brew install --cask android-platform-tools
     ```

---

## Configuring MuMuPlayer Pro

1. **Set Display Size**  
   - Open **Settings** → **Display** → **Display Size Phone**:  
     - Set **Device Display** to **1080 x 1920**.

2. **Enable ADB Debugging**  
   - Go to **Settings** → **Other**:  
     - Enable **ADB**: Select **Try to use the default port (5555)**.

3. **Start the Android Device**  
   - Launch the emulator in MuMuPlayer.

4. **Install and Launch a Supported Game**  
   - Install any game supported by **AdbAutoPlayer** and start it in the emulator.

5. **Verify ADB Connection**  
   - Open a Terminal and check for connected devices:  
     ```shell
     adb devices
     ```
   - If no devices are listed:  
     - Go to MuMuPlayer and click **Open ADB**:  
       ![Open ADB in MuMuPlayer](images/mumu_player_open_adb.png)  
     - Minimize and ignore the terminal window that opens with MuMuPlayer.

6. **Check for Devices Again**  
   - Return to your Terminal and verify that a device is listed:  
     ```shell
     adb devices
     ```

---

## Running AdbAutoPlayer

1. **Edit Configuration**  
   - Open the `main_config.toml` file in the **AdbAutoPlayer_MacOS** directory.  
   - Locate the `id` field and update `'emulator-5554'` with the device ID from the `adb devices` output.

2. **Open a Terminal**  
   - Navigate to the **AdbAutoPlayer_MacOS** directory in a new terminal:  
     ![Open Terminal in Folder](images/new_terminal_at_folder.png)

3. **Run AdbAutoPlayer**  
   - Execute the following command to start the tool:  
     ```shell
     ./AdbAutoPlayer
     ```

---

### Notes

- Ensure **ADB Debugging** is enabled in MuMuPlayer as described above.  
- If **AdbAutoPlayer** does not work, verify the following:
  - The correct device ID is specified in `main_config.toml`.
  - ADB is properly installed and configured (`adb devices` lists your emulator).  
- For additional help reach out on Discord: [@yules](https://discord.com/users/518169167048998913).
