param(
    [string]$Version = "dev"
)

$ErrorActionPreference = "Stop"

$Workspace = $env:GITHUB_WORKSPACE
$ReleaseZipDir = Join-Path $Workspace "AdbAutoPlayer"

if (Test-Path $ReleaseZipDir) {
    Remove-Item -Recurse -Force $ReleaseZipDir
}

if (-not $Workspace) {
    Write-Error "GITHUB_WORKSPACE environment variable is not set."
    exit 1
}

Write-Output "Running Wails build..."
wails build -devtools -ldflags "-X main.Version=$Version"


Write-Output "Running Nuitka build..."
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

Copy-Item -Path "$Workspace/cmd/wails/build/bin/AdbAutoPlayer.exe" -Destination $ReleaseZipDir -Force

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

foreach ($Item in $Items) {
    $DestPath = $Item.FullName.Replace($GamesSource, $GamesDir)
    if ($Item.PSIsContainer) {
        New-Item -ItemType Directory -Force -Path $DestPath
    } else {
        Copy-Item -Path $Item.FullName -Destination $DestPath -Force
    }
}

Copy-Item -Path "$Workspace/python/adb_auto_player/binaries/windows/*" -Destination $BinariesDir -Recurse -Force

$ZipFile = Join-Path $Workspace "AdbAutoPlayer_Windows.zip"
Compress-Archive -Path "$ReleaseZipDir\*" -DestinationPath $ZipFile -Force
Write-Output "ZIP file created at ${ZipFile}"

Write-Output "Files collected in ${ReleaseZipDir}:"
Get-ChildItem -Path $ReleaseZipDir -Recurse
