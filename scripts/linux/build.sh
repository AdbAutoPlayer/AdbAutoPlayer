#!/bin/bash

set -e

cd "$(dirname "$0")/../.."

PROJECT_NAME="adb-auto-player"
PYLIB_DIR="$(realpath src-tauri/pyembed/python/lib)"

export PYTAURI_STANDALONE="1"
PYO3_PYTHON="$(realpath src-tauri/pyembed/python/bin/python3)"
export PYO3_PYTHON
export RUSTFLAGS=" \
    -C link-arg=-Wl,-rpath,\$ORIGIN/../lib/$PROJECT_NAME/lib \
    -L $PYLIB_DIR"

uv pip install \
    --exact \
    --compile-bytecode \
    --python="$PYO3_PYTHON" \
    --reinstall-package="$PROJECT_NAME" \
    ./src-tauri

pnpm tauri build --config="src-tauri/tauri.bundle.json" --config="src-tauri/tauri.bundle.templates.json" -- --profile bundle-release
