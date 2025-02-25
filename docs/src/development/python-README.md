# Python README

## General
Set the python directory as the root of your project if you are using PyCharm.  
The `python/.idea` contains run configurations and other things that make setting up PyCharm easier for you.

## Windows
### Setup
> [!IMPORTANT]
> Execute commands in the python directory
1. Install [Python](https://www.python.org/downloads/)
2. Install [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer)
3. Create virtualenv and install
    ```shell
    poetry shell
    poetry install
    ```
4. You can run the CLI like this:
    ```shell
    poetry run adb-auto-player
    ```

## MacOS
### Setup
> [!IMPORTANT]
> Execute commands in the python directory
1. Install [Python](https://formulae.brew.sh/formula/python@3.12)
2. Install [Poetry](https://python-poetry.org/docs/#installing-with-pipx)
3. Install [Adb](https://formulae.brew.sh/cask/android-platform-tools)
4. Create virtualenv and install
   ```shell
   poetry shell
   poetry install
   ```
5. You can run the CLI like this:
   ```shell
   poetry run adb-auto-player
   ```

## Building the Executable
> [!IMPORTANT]
> You never really have to do this it's for documentation purposes only. If you want to develop use the poetry command and if you to build the App use the corresponding build script!
### Windows
```shell
poetry run nuitka --standalone --output-filename=adb_auto_player.exe --assume-yes-for-downloads --windows-console-mode=hide adb_auto_player/main.py
```

### MacOS
```shell
poetry run nuitka --standalone --output-filename=adb_auto_player_py_app --assume-yes-for-downloads adb_auto_player/main.py
```
