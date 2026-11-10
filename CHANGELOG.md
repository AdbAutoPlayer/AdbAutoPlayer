# Changelog

## [12.13.9] - 2026-11-10

### New Features

- **AFK Journey – New hero**: Added Thane to the hero list, so it can be recognized and selected.

### Bug Fixes

- **AFK Journey – Homestead**: Entering the Homestead now waits for the loading screen instead of pressing back too early. It also handles the "Tap to enter" screen after a game restart.
- **AFK Journey – Homestead crafting**: The "You have Process Cards available" popup that covered the crafting screen is now dismissed, and the crafting screen is retried instead of timing out.
- **AFK Journey – Battle start**: The battle start button is now retapped at intervals based on the template timeout setting, so a slow emulator gets more time to load the battle.
