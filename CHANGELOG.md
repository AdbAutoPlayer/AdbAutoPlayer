# Changelog

## [12.8.12] - 2026-05-08

### Fixed
- ⚖️ AFK Journey: Hero Scanner: Implemented dynamic scan limits (template count + 100) to prevent premature termination and future-proof for new hero releases.
- ⏭️ AFK Journey: Dura's Trials: Added recognition for the "Skip" button to prevent automation timeouts during cutscenes.
- 🖱️ AFK Journey: Quest Mode: Improved "Hold" button mechanics by using detected coordinates instead of hardcoded points.
- 🛡️ AFK Journey: Quest Mode: Added automatic handling for "Incomplete Formation" popups when starting battles.

### Changed
- 🔄 Synchronized with upstream AdbAutoPlayer:main.
- 🏷️ Bumped version to 12.8.12.

## [12.8.11] - 2026-05-05

### Added
- 🦀 Rust Settings Initialization: Fixed a critical bug where advanced settings were initialized with invalid zero values, causing Pydantic validation failures and UI slider issues.
