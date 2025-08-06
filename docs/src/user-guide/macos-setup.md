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
   Install Tesseract for optical character recognition (OCR):
   ```bash
   brew install tesseract
   ```

4. **Download AdbAutoPlayer**
   - Visit the [AdbAutoPlayer GitHub releases page](https://github.com/AdbAutoPlayer/AdbAutoPlayer/releases/latest) to download the latest `AdbAutoPlayer_MacOS.zip`.
   - Extract the `.zip` file to a folder on your computer.

## Additional Information

- **Read the Important Notes**  
  Inside the `AdbAutoPlayer_MacOS.zip`, review the [MACOS_READ_THIS_IMPORTANT.txt](https://github.com/AdbAutoPlayer/AdbAutoPlayer/tree/main/.github/scripts/MACOS_READ_THIS_IMPORTANT.txt) file for critical setup details.

- **Build Locally (Optional)**  
  To build the app from source, follow the instructions in the [Dev & Build Guide](../development/dev-and-build.md).
