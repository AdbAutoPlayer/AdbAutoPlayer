# Dev & Build

## Build scripts
### Windows .exe
```powershell
.github\scripts\build_windows.ps1
```

### MacOS .app Bundle
> [!IMPORTANT]
> macOS Gatekeeper will not allow unsigned .app Bundles to run on other devices.
> When you build it yourself it will run on your Mac but if you share it, it will be blocked.
```shell
.github/scripts/build_macos.sh
```

## CLI
Set the python directory as the root of your project if you are using PyCharm.  
The `python/.idea` contains run configurations and other things that make setting up PyCharm easier for you.  

### Dev Setup
> [!IMPORTANT]
> Execute these commands in the python directory
#### Windows
1. Install [uv](https://docs.astral.sh/uv/getting-started/installation).
2. Install Python.
    ```shell
    uv python install
    ```
3. Install dev dependencies.
   ```shell
   uv sync --dev
   ```
4. Install pre-commit.
   ```shell
   uvx pre-commit install
   ```
5. Verify the player runs on CLI by showing the help.
    ```shell
    uv run adb-auto-player -h
    ```

#### MacOS
1. Install [Homebrew](https://brew.sh/)
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation).
3. Install Python.
    ```shell
    uv python install
    ```
4. Install [ADB](https://formulae.brew.sh/cask/android-platform-tools)
5. Install [Tesseract](https://formulae.brew.sh/formula/tesseract)
6. Verify the player runs on CLI by showing the help.
    ```shell
    uv run adb-auto-player -h
    ```

#### Note:
UV creates a standard python virtual environment by default.
Standard Unix command:
```shell
source .venv/bin/activate
```
More examples in [UV Docs](https://docs.astral.sh/uv/pip/environments/#creating-a-virtual-environment).

## GUI Dev Build
1. Follow all the steps in the [CLI section](#cli)
2. Install [Go](https://go.dev/dl/)
3. Install [Node](https://nodejs.org/en/download/)
4. (MacOS) Install [Xcode](https://apps.apple.com/us/app/xcode/id497799835)
5. Install [Wails3](https://v3alpha.wails.io/getting-started/installation/#installation)
6. Run the dev command from the root directory
   ```shell
   wails3 dev
   ```
