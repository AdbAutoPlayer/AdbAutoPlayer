#!/bin/bash

mkdir -p $GITHUB_WORKSPACE/release_zip

cp cmd/wails/build/bin/AdbAutoPlayer.exe $GITHUB_WORKSPACE/release_zip/
cp cmd/wails/config.toml $GITHUB_WORKSPACE/release_zip/config.toml

cp python/adb_auto_player.exe $GITHUB_WORKSPACE/release_zip/

mkdir -p $GITHUB_WORKSPACE/release_zip/games/afk_journey/templates
cp -r python/adb_auto_player/games/afk_journey/templates $GITHUB_WORKSPACE/release_zip/games/afk_journey/templates
cp python/adb_auto_player/games/afk_journey/AFKJourney.toml $GITHUB_WORKSPACE/release_zip/games/afk_journey/AFKJourney.toml

echo "files collected in $GITHUB_WORKSPACE/release_zip"
