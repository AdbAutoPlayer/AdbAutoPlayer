# Changelog

## [12.12.3] - 2026-09-26

### Added

- **AFK Journey**: Added Karma to the hero list.

### Bug Fixes

- **Dura's Trials**: When Dura's Trials is locked (listed under "Coming Soon" in Battle Modes), the task failed with "Failed to tap: battle_modes/duras_trials.png, Template still visible." and aborted the whole Dailies run. It is now detected, skipped with a warning, and Dailies continue with the next step.
- **Navigation (Resonating Hall)**: The World overview was not recognized at night (the Homestead button moved to the bottom-right and the day/night icon doesn't match the moon-only variant), so navigating to the Resonating Hall never tapped its button and timed out 3 times. This affected Equip new Equipment and every other task going through the Resonating Hall.
- **Equip new Equipment**: After "Open all" the equipment rewards screen is now closed via its "Tap to close" hint instead of a single blind tap, which could leave the screen open and cost a full template timeout. The "Open all" retry loop is now correctly capped at 3 attempts.
- **ADB**: The "Multiple displays detected, targeting display …" message is now logged at debug level instead of info.
