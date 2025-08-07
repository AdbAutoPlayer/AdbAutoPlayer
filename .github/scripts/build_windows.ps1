param(
    [string]$Version = "0.0.0"
)

$ErrorActionPreference = "Stop"

Write-Output "Checking for required tools..."
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv is not installed or not found in PATH. Please install uv. https://adbautoplayer.github.io/AdbAutoPlayer/development/dev-and-build.html#cli"
    exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "npm is not installed or not found in PATH. Please install Node.js and npm. https://adbautoplayer.github.io/AdbAutoPlayer/development/dev-and-build.html#gui"
    exit 1
}
if (-not (Get-Command wails3 -ErrorAction SilentlyContinue)) {
    Write-Error "Wails3 is not installed or not found in PATH. Please install Wails3. https://adbautoplayer.github.io/AdbAutoPlayer/development/dev-and-build.html#gui"
    exit 1
}
Write-Output "All required tools (uv, npm, Wails3) are installed."

# Use GITHUB_WORKSPACE if set, otherwise default to two directories up from script location
$Workspace = $env:GITHUB_WORKSPACE
if (-not $Workspace) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $Workspace = Split-Path -Parent (Split-Path -Parent $ScriptDir)
}

$ReleaseZipDir = Join-Path $Workspace "AdbAutoPlayer"

if (Test-Path $ReleaseZipDir) {
    Remove-Item -Recurse -Force $ReleaseZipDir
}

Write-Output "Running Wails3 Task build..."
$env:VERSION="$Version"
$env:PRODUCTION="true"
wails3 task build

Write-Output "Running Nuitka build, this can take a long time..."
Push-Location (Join-Path $Workspace "python")

uv run nuitka --standalone --output-filename=adb_auto_player.exe --assume-yes-for-downloads --include-package=adb_auto_player.games --include-plugin-directory=adb_auto_player/games --follow-import-to=adb_auto_player.games --include-package=adb_auto_player.commands --include-plugin-directory=adb_auto_player/commands  --follow-import-to=adb_auto_player.commands --include-module=pkgutil --windows-console-mode=attach adb_auto_player/main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Nuitka failed with exit code $LASTEXITCODE"
    exit $LASTEXITCODE
}

if (Test-Path "nuitka-crash-report.xml") {
    Write-Host "Nuitka generated a crash report. Failing the build."
    Get-Content nuitka-crash-report.xml | Write-Host
    exit 1
}

Pop-Location

New-Item -ItemType Directory -Force -Path $ReleaseZipDir
$BinariesDir = Join-Path $ReleaseZipDir "binaries"
$GamesDir = Join-Path $ReleaseZipDir "games"

New-Item -ItemType Directory -Force -Path $BinariesDir
New-Item -ItemType Directory -Force -Path $GamesDir

Copy-Item -Path "$Workspace/bin/AdbAutoPlayer.exe" -Destination $ReleaseZipDir -Force

Copy-Item -Path "$Workspace/python/main.dist/*" -Destination $BinariesDir -Recurse -Force

# Copy everything from "games" except:
# - .py files
# - Directories that start with "_"
# - Any directory named "mixins"
$GamesSource = Join-Path $Workspace "python/adb_auto_player/games"
$Items = Get-ChildItem -Path $GamesSource -Recurse | Where-Object {
    -not ($_.FullName -match '\\_') -and      # Exclude directories starting with "_"
    -not ($_.FullName -match '\\mixins($|\\)') -and  # Exclude directories named "mixins"
    -not ($_.Extension -eq '.py') -and        # Exclude .py files
    -not ($_.Extension -eq '.toml')           # Exclude .toml files
}

foreach ($Item in $Items) {
    $DestPath = $Item.FullName.Replace($GamesSource, $GamesDir)
    if ($Item.PSIsContainer) {
        New-Item -ItemType Directory -Force -Path $DestPath
    } else {
        Copy-Item -Path $Item.FullName -Destination $DestPath -Force
    }
}

Copy-Item -Path "$Workspace/python/adb_auto_player/binaries/windows/*" -Destination $BinariesDir -Recurse -Force

Write-Output "Build completed successfully. Artifacts are organized in $ReleaseZipDir"
