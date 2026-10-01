# Changelog

## [12.13.1] - 2026-10-01

### Added

- **UI – Error screenshots folder**: New "screenshots" button in the log panel that opens the folder with the debug screenshots of the current profile. The folder is created if it doesn't exist yet.

### Bug Fixes

- **AFK Journey – Quests**: On the AFK Stages formation screen the quest loop matched the same green "Battle" button and kept going Battle → Back → Battle forever. The formation title is now read with OCR: on an AFK Stages screen ("AFK Stage N" / "Season … Stage N") the task goes back to the World instead. A debug screenshot is also saved before the blind tap used to close full-screen popups, so bug reports show what was on screen.
