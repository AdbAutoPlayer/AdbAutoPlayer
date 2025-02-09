#!/bin/bash

WORKSPACE="${GITHUB_WORKSPACE}"
RELEASE_ZIP_DIR="${WORKSPACE}/release_zip"
BINARIES_DIR="${RELEASE_ZIP_DIR}/binaries"

# Create directory structure
mkdir -p "${RELEASE_ZIP_DIR}/games/afk_journey/templates"
mkdir -p "${BINARIES_DIR}"

# Copy files
cp "cmd/wails/build/bin/AdbAutoPlayer.app/Contents/MacOS/AdbAutoPlayer" "${RELEASE_ZIP_DIR}/"
cp "cmd/wails/config.toml" "${RELEASE_ZIP_DIR}/"

# Copy contents of "python/main.dist" dir into BINARIES_DIR
cp -r "python/main.dist/." "${BINARIES_DIR}/"

# Copy templates and config
cp -r "python/adb_auto_player/games/afk_journey/templates/"* "${RELEASE_ZIP_DIR}/games/afk_journey/templates/"
cp "python/adb_auto_player/games/afk_journey/AFKJourney.toml" "${RELEASE_ZIP_DIR}/games/afk_journey/"

echo "Files collected in ${RELEASE_ZIP_DIR}:"
ls -R "${RELEASE_ZIP_DIR}"

# Create main ZIP file
cd "${RELEASE_ZIP_DIR}"
zip -r "${WORKSPACE}/AdbAutoPlayer_MacOS.zip" ./*
echo "ZIP file created at ${WORKSPACE}/AdbAutoPlayer_MacOS.zip"

# Create patch ZIP
PATCH_DIR="${WORKSPACE}/Patch_MacOS"
mkdir -p "${PATCH_DIR}"
cp -r "${RELEASE_ZIP_DIR}/games" "${PATCH_DIR}/"
cp -r "${BINARIES_DIR}" "${PATCH_DIR}/"

cd "${PATCH_DIR}"
zip -r "${WORKSPACE}/Patch_MacOS.zip" ./*
echo "Patch ZIP file created at ${WORKSPACE}/Patch_MacOS.zip"
