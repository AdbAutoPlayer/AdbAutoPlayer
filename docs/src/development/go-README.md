# Go README

## Setup
Follow the Installation guide here:
[https://wails.io/docs/gettingstarted/installation](https://wails.io/docs/gettingstarted/installation)  
You can ignore the Optional Dependencies section.

### Start the App in development mode
```shell
cd .\cmd\wails\
wails dev
```

### Building Python Executable
Follow the [Python README](https://github.com/yulesxoxo/AdbAutoPlayer/blob/main/docs/src/development/python-README.md) and when you are done try the build command this can take up to 30 minutes:
> [!IMPORTANT]
> Execute the build command in the python directory
#### Windows
```shell
uv run nuitka --standalone --output-filename=adb_auto_player.exe --assume-yes-for-downloads --windows-console-mode=hide adb_auto_player/main.py
```

#### MacOS
```shell
uv run nuitka --standalone --output-filename=adb_auto_player_py_app --assume-yes-for-downloads adb_auto_player/main.py
```
