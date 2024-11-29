# AdbAutoPlayer
App is only tested on Windows using [LDPlayer](https://www.ldplayer.net/)
I have tried it once on an Apple M1 Max using [MuMuPlayer Pro](https://www.mumuplayer.com/mac/)
While it should work on Apple silicon I do not plan to officially support it or deal with any issues personally.

## Windows Native Setup
1. Install [Python](https://www.python.org/downloads/)
2. Install [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer)
3. Create virtualenv and install
   ```shell
   poetry shell
   poetry install
   poetry run pre-commit install
   ```

## MacOS Setup
1. Install [Python](https://formulae.brew.sh/formula/python@3.12)
2. Install [Poetry](https://python-poetry.org/docs/#installing-with-pipx)
3. Install [Adb](https://formulae.brew.sh/cask/android-platform-tools)
4. Create virtualenv and install
   ```shell
   poetry shell
   poetry install
   poetry run pre-commit install
   ```

## Supported Games
- AFKJourney

## Planned Future Support
- Infinity Nikki
- Pokemon TCG Pocket

## Build .exe
```shell
poetry run pyinstaller --clean windows.spec
cp adb_auto_player/main_config.toml dist
cp -r adb_auto_player/plugins dist/plugins
```

## Build macos binary
```
poetry run pyinstaller --clean macos.spec
cp adb_auto_player/main_config.toml dist
cp -r adb_auto_player/plugins dist/plugins
```
