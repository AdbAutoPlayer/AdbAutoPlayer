param(
    [switch]$cli
)

$ErrorActionPreference = "Stop"

$Workspace = $env:GITHUB_WORKSPACE
$ReleaseZipDir = Join-Path $Workspace "AdbAutoPlayer"
$PatchDir = Join-Path $Workspace "Patch_Windows"

if (Test-Path $ReleaseZipDir) {
    Remove-Item -Recurse -Force $ReleaseZipDir
}
if (Test-Path $PatchDir) {
    Remove-Item -Recurse -Force $PatchDir
}

if (-not $Workspace) {
    Write-Error "GITHUB_WORKSPACE environment variable is not set."
    exit 1
}

if (-not $cli) {
    Write-Output "Running Wails build..."
    Push-Location (Join-Path $Workspace "cmd/wails")
    wails build -devtools
    Pop-Location
}

Write-Output "Running Nuitka build..."
Push-Location (Join-Path $Workspace "python")
if (-not $cli) {
    poetry run nuitka --standalone --output-filename=adb_auto_player.exe --assume-yes-for-downloads --windows-console-mode=attach adb_auto_player/main.py
} else {
    poetry run nuitka --standalone --output-filename=adb_auto_player.exe --assume-yes-for-downloads --windows-console-mode=force adb_auto_player/main.py
}
Pop-Location

New-Item -ItemType Directory -Force -Path $ReleaseZipDir
$BinariesDir = Join-Path $ReleaseZipDir "binaries"
$GamesDir = Join-Path $ReleaseZipDir "games"

New-Item -ItemType Directory -Force -Path $BinariesDir
New-Item -ItemType Directory -Force -Path $GamesDir

if (-not $cli) {
    Copy-Item -Path "$Workspace/cmd/wails/build/bin/AdbAutoPlayer.exe" -Destination $ReleaseZipDir -Force
}

Copy-Item -Path "$Workspace/config/config.toml" -Destination $ReleaseZipDir -Force
Copy-Item -Path "$Workspace/python/main.dist/*" -Destination $BinariesDir -Recurse -Force

# Copy everything from "games" except:
# - .py files
# - Directories that start with "_"
# - Any directory named "mixins"
$GamesSource = Join-Path $Workspace "python/adb_auto_player/games"
$Items = Get-ChildItem -Path $GamesSource -Recurse | Where-Object {
    -not ($_.FullName -match '\\_') -and      # Exclude directories starting with "_"
    -not ($_.FullName -match '\\mixins($|\\)') -and  # Exclude directories named "mixins"
    -not ($_.Extension -eq '.py')             # Exclude .py files
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

if (-not $cli) {
    New-Item -ItemType Directory -Force -Path $PatchDir
    Copy-Item -Path (Join-Path $ReleaseZipDir "games") -Destination $PatchDir -Recurse -Force
    Copy-Item -Path $BinariesDir -Destination $PatchDir -Recurse -Force
    $PatchZipFile = Join-Path $Workspace "Patch_Windows.zip"
    Compress-Archive -Path "$PatchDir\*" -DestinationPath $PatchZipFile -Force
    Write-Output "Patch ZIP file created at ${PatchZipFile}"
}

# We are only shipping static binaries for the full .zip
# If we ever need to update them we should add a flag to conditionally add them to Patch
Copy-Item -Path "$Workspace/python/adb_auto_player/binaries/windows/*" -Destination $BinariesDir -Recurse -Force

if (-not $cli) {
    $ZipFile = Join-Path $Workspace "AdbAutoPlayer_Windows.zip"
    Compress-Archive -Path "$ReleaseZipDir\*" -DestinationPath $ZipFile -Force
    Write-Output "ZIP file created at ${ZipFile}"

}




Write-Output "Files collected in ${ReleaseZipDir}:"
Get-ChildItem -Path $ReleaseZipDir -Recurse
