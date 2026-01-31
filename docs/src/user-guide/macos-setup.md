# macOS Setup Guide

> [!IMPORTANT]
> Ensure you have reviewed the [Emulator Settings](emulator-settings.md) before proceeding.

## Installation Steps

1. **Install Homebrew**  
   Download and install [Homebrew](https://brew.sh/) by following the instructions on their official website.

2. **Install ADB**  
   Use Homebrew to install Android Debug Bridge (ADB):
   ```bash
   brew install --cask android-platform-tools
   ```

3. **Install Tesseract**  
   Used for optical character recognition (OCR):
   ```bash
   brew install tesseract
   ```

4. **Download AdbAutoPlayer**
   - Visit the [AdbAutoPlayer GitHub releases page](https://github.com/AdbAutoPlayer/AdbAutoPlayer/releases/latest) to download the latest `AdbAutoPlayer_aarch64.app.tar.gz`.
   - Extract the `.tar.gz` file to a folder on your computer.
   - Follow the Instructions in the `MACOS_READ_THIS_IMPORTANT.txt` you can also find in the releases page [AdbAutoPlayer GitHub releases page](https://github.com/AdbAutoPlayer/AdbAutoPlayer/releases/latest)

## Additional Information

- **Build Locally (Optional)**  
  To build the app from source, follow the instructions in the [Dev & Build Guide](../development/dev-and-build.md).
