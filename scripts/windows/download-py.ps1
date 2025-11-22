### Argument ###

$PYTHON_VERSION = "3.14.0"  # update these by yourself
$TAG = "20251031"  # update these by yourself
$TARGET = "x86_64-pc-windows-msvc"

################

$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")

$url = "https://github.com/astral-sh/python-build-standalone/releases/download/${TAG}/cpython-${PYTHON_VERSION}+${TAG}-${TARGET}-install_only_stripped.tar.gz"

$DEST_DIR = "src-tauri\pyembed"

# Ensure DEST_DIR exists
New-Item -ItemType Directory -Path $DEST_DIR -Force | Out-Null

# Delete contents if not empty
if ((Get-ChildItem -Path $DEST_DIR).Count -gt 0) {
    Write-Host "Clearing existing contents of $DEST_DIR..."
    Remove-Item "$DEST_DIR\*" -Recurse -Force
}

$TEMP_FILE = ".python-standalone.tar.gz"
try {
    curl.exe -L "$url" -o "$TEMP_FILE"
    tar.exe -xzf "$TEMP_FILE" -C "$DEST_DIR"
}
finally {
    Remove-Item "$TEMP_FILE"
}
