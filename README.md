# AdbAutoPlayer

## Windows Native Setup
1. Install [Python](https://www.python.org/downloads/)
2. Install [Poetry](https://python-poetry.org/docs/#installing-with-the-official-installer)
3. Create virtualenv and install
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
poetry run pyinstaller --clean main.spec
cp adb_auto_player/main_config.toml dist
cp -r adb_auto_player/plugins dist
```
