#!/bin/bash
set -e

if [[ -z "${GITHUB_WORKSPACE}" ]]; then
  echo "Error: GITHUB_WORKSPACE is not set."
  exit 1
fi


WORKSPACE="${GITHUB_WORKSPACE}"

RELEASE_ZIP_DIR="${WORKSPACE}/release_zip"
PATCH_DIR="${WORKSPACE}/Patch_MacOS"
ZIP_FILE="${WORKSPACE}/AdbAutoPlayer_MacOS.zip"
PATCH_ZIP_FILE="${WORKSPACE}/Patch_MacOS.zip"

for TARGET in "${RELEASE_ZIP_DIR}" "${PATCH_DIR}" "${ZIP_FILE}" "${PATCH_ZIP_FILE}"; do
  if [ -d "$TARGET" ]; then
    rm -rf "$TARGET"
    echo "Deleted directory: $TARGET"
  elif [ -f "$TARGET" ]; then
    rm -f "$TARGET"
    echo "Deleted file: $TARGET"
  else
    echo "Not found: $TARGET"
  fi
done

BINARIES_DIR="${RELEASE_ZIP_DIR}/binaries"

# Create directory structure
mkdir -p "${RELEASE_ZIP_DIR}/games"
mkdir -p "${BINARIES_DIR}"

# Use find to copy all files from ${WORKSPACE}/python/adb_auto_player/games to ${RELEASE_ZIP_DIR}/games
# and keep the directory structure except:
# - .py files
# - .toml files
# - Directories starting with "_"
# - Any directory named "mixins"
find "${WORKSPACE}/python/adb_auto_player/games" -type f \
  -not -path "*/\_*/*" \
  -not -path "*/mixins/*" \
  -not -name "*.py" \
  -not -name "*.toml" \
  -print0 | while IFS= read -r -d '' file; do
    # Get the relative path from the source directory
    rel_path="${file#"${WORKSPACE}"/python/adb_auto_player/games/}"
    # Create the destination directory
    dest_dir="${RELEASE_ZIP_DIR}/games/$(dirname "$rel_path")"
    mkdir -p "$dest_dir"
    # Copy the file
    cp "$file" "${RELEASE_ZIP_DIR}/games/$rel_path"
    echo "Copied: $rel_path"
done


echo "Running Wails build..."
pushd "${WORKSPACE}/cmd/wails" > /dev/null
wails build -devtools
popd > /dev/null

# would be the "correct" way to do it but macOS flags unsigned apps as "damaged" and refuses to execute them
# cp -r "cmd/wails/build/bin/AdbAutoPlayer.app" "${RELEASE_ZIP_DIR}/"
# Copy main binary (handling macOS unsigned app issue)
cp "cmd/wails/build/bin/AdbAutoPlayer.app/Contents/MacOS/AdbAutoPlayer" "${RELEASE_ZIP_DIR}/"

echo "Running Nuitka build..."
pushd "${WORKSPACE}/python" > /dev/null
uv run nuitka --standalone --output-filename=adb_auto_player_py_app --assume-yes-for-downloads adb_auto_player/main.py
popd > /dev/null

# Copy compiled Nuitka binary
cp -r "python/main.dist/." "${BINARIES_DIR}/"

echo "Files collected in ${RELEASE_ZIP_DIR}:"
ls -R "${RELEASE_ZIP_DIR}"

# Create main ZIP file
cd "${RELEASE_ZIP_DIR}" || exit 1
zip -r "${ZIP_FILE}" ./*
echo "ZIP file created at ${ZIP_FILE}"

# Create patch ZIP
mkdir -p "${PATCH_DIR}"
cp -r "${RELEASE_ZIP_DIR}/games" "${PATCH_DIR}/"
cp -r "${BINARIES_DIR}" "${PATCH_DIR}/"

cd "${PATCH_DIR}" || exit 1
zip -r "${PATCH_ZIP_FILE}" ./*
echo "Patch ZIP file created at ${PATCH_ZIP_FILE}"
