#!/bin/bash

# Exit on any error
set -e

# Default version if not provided
VERSION="${1:-0.0.0}"

echo "Checking for required tools..."
if ! command -v uv >/dev/null 2>&1; then
    echo "Error: uv is not installed or not found in PATH. Please install uv. https://adbautoplayer.github.io/AdbAutoPlayer/development/dev-and-build.html#cli"
    exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
    echo "Error: npm is not installed or not found in PATH. Please install Node.js and npm. https://adbautoplayer.github.io/AdbAutoPlayer/development/dev-and-build.html#gui"
    exit 1
fi
if ! command -v wails3 >/dev/null 2>&1; then
    echo "Error: Wails3 is not installed or not found in PATH. Please install Wails3. https://adbautoplayer.github.io/AdbAutoPlayer/development/dev-and-build.html#gui"
    exit 1
fi
echo "All required tools (uv, npm, Wails3) are installed."

# Use GITHUB_WORKSPACE if set, otherwise default to two directories up from script location
WORKSPACE="${GITHUB_WORKSPACE:-$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")}"

rm -rf "$WORKSPACE/AdbAutoPlayer.app"

echo "Workspace: $WORKSPACE"

echo "Running Wails3 Task build..."
export VERSION="$VERSION"
export PRODUCTION="true"
# this creates $WORKSPACE/bin/AdbAutoPlayer.app
wails3 task package


if [ "${SKIP_NUITKA:-false}" = "false" ]; then
    echo "Running Nuitka build, this can take a long time..."
    pushd "$WORKSPACE/python"

    if ! uv run nuitka --standalone --output-filename=adb_auto_player --assume-yes-for-downloads --include-package=adb_auto_player.games --include-plugin-directory=adb_auto_player/games --follow-import-to=adb_auto_player.games --include-package=adb_auto_player.commands --include-plugin-directory=adb_auto_player/commands --follow-import-to=adb_auto_player.commands --include-module=pkgutil adb_auto_player/main.py; then
        echo "Nuitka failed with exit code $?"
        exit 1
    fi

    if [ -f "nuitka-crash-report.xml" ]; then
        echo "Nuitka generated a crash report. Failing the build."
        cat nuitka-crash-report.xml
        exit 1
    fi

    popd
else
    echo "Skipping Nuitka build as SKIP_NUITKA environment variable is set to true"
fi

# Move the .app bundle to the root directory
mv "$WORKSPACE/bin/AdbAutoPlayer.app" "$WORKSPACE"

# Create directories for release
BINARIES_DIR="$WORKSPACE/AdbAutoPlayer.app/Contents/Resources/binaries"
GAMES_DIR="$WORKSPACE/AdbAutoPlayer.app/Contents/Resources/games"
mkdir -p "$BINARIES_DIR"
mkdir -p "$GAMES_DIR"
# Copy Nuitka output to binaries directory
cp -r "$WORKSPACE/python/main.dist/"* "$BINARIES_DIR/"

# Copy game assets, excluding .py, .toml, directories starting with _, and mixins directories
GAMES_SOURCE="$WORKSPACE/python/adb_auto_player/games"
find "$GAMES_SOURCE" -type f -not -name "*.py" -not -name "*.toml" -not -path "*/_*" -not -path "*/mixins/*" | while read -r item; do
    DEST_PATH="${item/$GAMES_SOURCE/$GAMES_DIR}"
    mkdir -p "$(dirname "$DEST_PATH")"
    cp "$item" "$DEST_PATH"
done
find "$GAMES_SOURCE" -type d -not -path "*/_*" -not -path "*/mixins/*" | while read -r dir; do
    DEST_PATH="${dir/$GAMES_SOURCE/$GAMES_DIR}"
    mkdir -p "$DEST_PATH"
done

codesign --force --deep --sign - "$WORKSPACE/AdbAutoPlayer.app"

echo "Build completed successfully, .app Bundle can be found in: $WORKSPACE"
