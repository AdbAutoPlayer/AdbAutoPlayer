#!/bin/bash

WORKSPACE="${GITHUB_WORKSPACE}"
RELEASE_ZIP_DIR="${WORKSPACE}/release_zip"

# Create directory structure
mkdir -p "${RELEASE_ZIP_DIR}/games/afk_journey/templates"

# Copy files
cp "cmd/wails/build/bin/AdbAutoPlayer" "${RELEASE_ZIP_DIR}/"
cp "cmd/wails/config.toml" "${RELEASE_ZIP_DIR}/"
cp "python/adb_auto_player.bin" "${RELEASE_ZIP_DIR}/games/"

# Copy templates and config
cp -r "python/adb_auto_player/games/afk_journey/templates/"* "${RELEASE_ZIP_DIR}/games/afk_journey/templates/"
cp "python/adb_auto_player/games/afk_journey/AFKJourney.toml" "${RELEASE_ZIP_DIR}/games/afk_journey/"

echo "Files collected in ${RELEASE_ZIP_DIR}:"
ls -R "${RELEASE_ZIP_DIR}"

# Create main ZIP file
cd "${RELEASE_ZIP_DIR}"
zip -r "${WORKSPACE}/AdbAutoPlayer_MacOS_arm64.zip" ./*
echo "ZIP file created at ${WORKSPACE}/AdbAutoPlayer_MacOS_arm64.zip"

# Create patch ZIP
PATCH_DIR="${WORKSPACE}/Patch_MacOS"
mkdir -p "${PATCH_DIR}"
cp -r "${RELEASE_ZIP_DIR}/games" "${PATCH_DIR}/"

cd "${PATCH_DIR}"
zip -r "${WORKSPACE}/Patch_MacOS_arm64.zip" ./*
echo "Patch ZIP file created at ${WORKSPACE}/Patch_MacOS_arm64.zip"
