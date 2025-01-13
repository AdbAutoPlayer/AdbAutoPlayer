# Python

## Windows Native Setup
1. Install [Python](https://www.python.org/downloads/)
2. Install [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer)
3. Create virtualenv and install
   ```shell
   poetry shell
   poetry install
   ```

## MacOS Setup
1. Install [Python](https://formulae.brew.sh/formula/python@3.12)
2. Install [Poetry](https://python-poetry.org/docs/#installing-with-pipx)
3. Install [Adb](https://formulae.brew.sh/cask/android-platform-tools)
4. Create virtualenv and install
   ```shell
   poetry shell
   poetry install
   ```

## Build
```shell
poetry run nuitka --standalone --onefile --output-filename=adb_auto_player.exe --assume-yes-for-downloads --windows-console-mode=disable adb_auto_player/main.py 
```
