# Dev & Build

## CLI
Set the python directory as the root of your project if you are using PyCharm.  
The `python/.idea` contains run configurations and other things that make setting up PyCharm easier for you.  

### Setup
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
1. Install [uv](https://docs.astral.sh/uv/getting-started/installation).
2. Install Python.
    ```shell
    uv python install
    ```
3. Install [ADB](https://formulae.brew.sh/cask/android-platform-tools)
4. Install [Tesseract](https://formulae.brew.sh/formula/tesseract)
5. Verify the player runs on CLI by showing the help.
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

## GUI
1. Follow all the steps in the [CLI section](#cli)
2. Install everything required for [Wails](https://wails.io/docs/gettingstarted/installation/).
   You can ignore the Optional Dependencies section.
3. Run the dev command from the root directory
   ```shell
   wails dev
   ```

## Build scripts
### Windows build_zip.ps1
```powershell
$env:GITHUB_WORKSPACE = "C:\Users\$env:USERNAME\GolandProjects\AdbAutoPlayer"; .github\scripts\build_zip.ps1
```
