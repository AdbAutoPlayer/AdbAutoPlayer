#!/bin/bash

### Argument ###

PYTHON_VERSION="3.13.9"  # update these by yourself
TAG="20251031"  # update these by yourself
TARGET="aarch64-apple-darwin"

################

set -e

cd "$(dirname "$0")/../.."

url="https://github.com/astral-sh/python-build-standalone/releases/download/${TAG}/cpython-${PYTHON_VERSION}+${TAG}-${TARGET}-install_only_stripped.tar.gz"

DEST_DIR="src-tauri/pyembed"
mkdir "$DEST_DIR"
curl -L "$url" | tar -xz -C "$DEST_DIR"

# ref: <https://github.com/pytauri/pytauri/issues/99#issuecomment-2704556726>
python_major_minor="${PYTHON_VERSION%.*}"  # "3.13.7" -> "3.13"
install_name_tool -id "@rpath/libpython$python_major_minor.dylib" "$DEST_DIR/python/lib/libpython$python_major_minor.dylib"
