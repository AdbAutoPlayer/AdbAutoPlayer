# Python README

## General
Set the python directory as the root of your project if you are using PyCharm.  
The `python/.idea` contains run configurations and other things that make setting up PyCharm easier for you.  
If you only want to develop bots or run it in CLI you do not have to set up Go and the Frontend.

## Setup
> [!IMPORTANT]
> Execute these commands in the python directory
### Windows
1. Install [UV](https://github.com/astral-sh/uv).
    ```shell
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
2. Install Python.
    ```shell
    uv python install
    ```
3. Verify the player runs on CLI by showing the help.
    ```shell
    uv run adb-auto-player -h
    ```

### MacOS
1. Install [UV](https://github.com/astral-sh/uv).
    ```shell
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
2. Install Python.
    ```shell
    uv python install
    ```
3. Install [Adb](https://formulae.brew.sh/cask/android-platform-tools)
4. Verify the player runs on CLI by showing the help.
    ```shell
    uv run adb-auto-player -h
    ```

## Note:
UV creates a standard python virtual environment by default.
Standard Unix command:
```shell
source .venv/bin/activate
```
More examples in [UV Docs](https://docs.astral.sh/uv/pip/environments/#creating-a-virtual-environment).
