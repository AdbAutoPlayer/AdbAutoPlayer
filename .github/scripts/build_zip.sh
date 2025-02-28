#!/bin/bash
set -e

if [[ -z "${GITHUB_WORKSPACE}" ]]; then
  echo "Error: GITHUB_WORKSPACE is not set."
  exit 1
fi

WORKSPACE="${GITHUB_WORKSPACE}"
RELEASE_ZIP_DIR="${WORKSPACE}/release_zip"
BINARIES_DIR="${RELEASE_ZIP_DIR}/binaries"

echo "Running Wails build..."
pushd "${WORKSPACE}/cmd/wails" > /dev/null
wails build -devtools
popd > /dev/null

echo "Running Nuitka build..."
pushd "${WORKSPACE}/python" > /dev/null
poetry run nuitka --standalone --output-filename=adb_auto_player_py_app --assume-yes-for-downloads adb_auto_player/main.py
popd > /dev/null

# Create directory structure
mkdir -p "${RELEASE_ZIP_DIR}/games"
mkdir -p "${BINARIES_DIR}"

# would be the "correct" way to do it but macOS flags unsigned apps as "damaged" and refuses to execute them
# cp -r "cmd/wails/build/bin/AdbAutoPlayer.app" "${RELEASE_ZIP_DIR}/"
# Copy main binary (handling macOS unsigned app issue)
cp "cmd/wails/build/bin/AdbAutoPlayer.app/Contents/MacOS/AdbAutoPlayer" "${RELEASE_ZIP_DIR}/"
cp "cmd/wails/config.toml" "${RELEASE_ZIP_DIR}/"

# Copy compiled Nuitka binary
cp -r "python/main.dist/." "${BINARIES_DIR}/"

# Use find to copy all files from python/adb_auto_player/games except:
# - .py files
# - Directories starting with "_"
# - Any directory named "mixins"
find "${WORKSPACE}/python/adb_auto_player/games" \
  -type f ! -name "*.py" \
  -exec cp --parents {} "${RELEASE_ZIP_DIR}/" \;

find "${WORKSPACE}/python/adb_auto_player/games" \
  -type d ! -name "_*" ! -name "mixins" \
  -exec cp -r --parents {} "${RELEASE_ZIP_DIR}/" \;

echo "Files collected in ${RELEASE_ZIP_DIR}:"
ls -R "${RELEASE_ZIP_DIR}"

# Create main ZIP file
cd "${RELEASE_ZIP_DIR}" || exit 1
zip -r "${WORKSPACE}/AdbAutoPlayer_MacOS.zip" ./*
echo "ZIP file created at ${WORKSPACE}/AdbAutoPlayer_MacOS.zip"

# Create patch ZIP
PATCH_DIR="${WORKSPACE}/Patch_MacOS"
mkdir -p "${PATCH_DIR}"
cp -r "${RELEASE_ZIP_DIR}/games" "${PATCH_DIR}/"
cp -r "${BINARIES_DIR}" "${PATCH_DIR}/"

cd "${PATCH_DIR}" || exit 1
zip -r "${WORKSPACE}/Patch_MacOS.zip" ./*
echo "Patch ZIP file created at ${WORKSPACE}/Patch_MacOS.zip"
