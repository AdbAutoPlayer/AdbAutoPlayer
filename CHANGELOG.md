# Changelog

## [12.13.3] - 2026-10-03

### Bug Fixes

- **Guild Manager Scan – Rankings**: Misread rank badges no longer put players at the wrong rank, and missing ranks are filled in from the list order when possible. Stray text and rank digits are no longer picked up as part of player names.
- **Guild Manager Scan – Supreme Arena**: The guild name is no longer taken as the player name, and Korean / Cyrillic names are now recovered here too.
- **Guild Manager Scan – Name matching**: Partially misread Korean names are recovered more reliably, and Latin or Japanese names are no longer wrongly matched to Korean members.
- **Guild Manager Scan – Activeness & Chest contributions**: Role labels no longer steal a member's value, chest counts misread with an extra leading digit are corrected, similar names are no longer merged, and only guild members are added from the chest list.
