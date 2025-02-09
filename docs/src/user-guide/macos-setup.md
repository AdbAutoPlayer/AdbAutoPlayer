# macOS Setup Guide

This guide walks you through setting up **AdbAutoPlayer** on macOS (Apple Silicon).

> [!IMPORTANT]
> Check [Emulator Settings](emulator-settings.md) if you haven't already!

---

## Installation Steps

### 1. **Download the Tool**
- Get the latest release of **AdbAutoPlayer**:
  [AdbAutoPlayer_MacOS.zip](https://github.com/yulesxoxo/AdbAutoPlayer/releases/latest).
- Extract the `.zip` file to a folder on your computer.

### 2. **Install Homebrew**
- Follow the instructions at [brew.sh](https://brew.sh/) to install **Homebrew**, a package manager for macOS.

### 3. **Install ADB via Homebrew**
- Use Homebrew to install the Android Debug Bridge (ADB):
  ```bash
  brew install --cask android-platform-tools
  ```

---

## Starting AdbAutoPlayer

macOS may block the app because it lacks a code signing certificate. Here's how to open it:

1. Double-click the app. You'll see this prompt:
   ![Blocked Prompt](../images/macos/not_opened.png)
   Click **Done**.

2. Go to **System Settings** → **Privacy & Security**, scroll to the bottom, and find:
   ![Blocked by macOS](../images/macos/was_blocked_to_protect_your_mac.png)
   Click **Open Anyway**.

3. Double-click the app again. If prompted, click **Open Anyway** again:
   ![Open AdbAutoPlayer](../images/macos/open_adb_auto_player.png).

4. If you see this security prompt:
   ![Security Prompt](../images/macos/privacy_and_security.png)
   Use your Touch ID or password.

5. The app will open a Terminal window. Wait for it to load.

# Continue to the [Troubleshooting Guide](troubleshoot.md)
