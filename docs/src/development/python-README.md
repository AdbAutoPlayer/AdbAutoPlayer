# Python README

## General
Set the python directory as the root of your project if you are using PyCharm.  
The `python/.idea` contains run configurations and other things that make setting up PyCharm easier for you.  
If you only want to develop bots or run it in CLI you do not have to set up Go and the Frontend.

## Setup
> [!IMPORTANT]
> Execute these commands in the python directory
### Windows
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

### MacOS
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
