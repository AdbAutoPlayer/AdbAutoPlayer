# Changelog

## [12.9.3] - 2026-05-29

### Features

- **ADB Device Scanner**: Added an automated ADB process and port scanner in the Device Settings form. It automatically detects running emulators (such as LDPlayer, BlueStacks, Nox, MEmu, MuMu, and Android Studio Emulator) and finds their active ADB ports, auto-filling the Device ID field.

### Bug Fixes

- **Auto-Progress Quests**: Fixed map repeatedly opening and closing by dynamically offset tapping the quest tracker text relative to the detected questbook icon, rather than using a hardcoded coordinate.
