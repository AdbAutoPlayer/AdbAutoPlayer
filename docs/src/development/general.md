# General

Versioning and Self-Updater will be completely revised when Wails v3 releases and a self-updater plugin is created: [GitHub Issue](https://github.com/wailsapp/wails/issues/1178)

## Versioning

The current versioning scheme works as follows:

- **Major**: Any change that requires downloading the latest version. This includes changes like to the Go-Python IPC API, a new build using Wails v3 with a proper self-updater, or major GUI changes requiring significant changes in the API that break backward compatibility.

- **Minor**: Changes to the Go Backend or Frontend that cannot be updated using the self-updater but do not affect functionality. Examples include purely aesthetic GUI changes.

- **Patch**: Any change to the Python Bot that do not affect the Go-Python IPC API.

## Self-Updater

The self-updater automatically downloads the `Patch_*.zip` and overwrites existing files.

- It only applies to **Minor** and **Patch** version updates.
- For a **Major** version update, the user will be asked to download the latest version and replace the app completely.

## Installing Pre-commit
We will assume you have uv installed otherwise go to [Python README](https://github.com/yulesxoxo/AdbAutoPlayer/blob/main/docs/src/development/python-README.md)

> [!IMPORTANT]
> Execute these commands in the project root directory

```shell
uvx pre-commit
```

## Build scripts
### Windows build_zip.ps1
```powershell
$env:GITHUB_WORKSPACE = "C:\Users\$env:USERNAME\GolandProjects\AdbAutoPlayer"; .github\scripts\build_zip.ps1
```

Python CLI only:
```powershell
$env:GITHUB_WORKSPACE = "C:\Users\$env:USERNAME\GolandProjects\AdbAutoPlayer"; .github\scripts\build_zip.ps1 -cli
```

### MacOS build_zip.sh
```shell
GITHUB_WORKSPACE=/Users/$USER/GolandProjects/AdbAutoPlayer bash ./.github/scripts/build_zip.sh
```
