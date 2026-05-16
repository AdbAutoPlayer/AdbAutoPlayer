# Changelog

## [12.8.19] - 2026-05-16

### Fixed

- ⚔️ **AFK Journey**: Enhanced Ravaged Realm automation reliability by updating the `Immortal_Squad_Open.png` template to accurately detect the new "Endless" seasonal UI variant.
- ⚔️ **AFK Journey**: Improved faction template matching for all Ravaged Realm squads (Graveborn, Wilder, Lightbearer) by dynamically cropping the attempt counter section from the templates, ensuring matching stability regardless of attempts consumed.
- ⚔️ **AFK Journey**: Fixed a false-positive click issue in the Ravaged Realm battle setup where the bot would mistakenly click empty space "in alto" (above the battle button); increased the battle button detection threshold from 15% to 75% to prevent interference from character rendering or UI gradients.

## [12.8.18] - 2026-05-13

### Fixed

- ⚔️ **AFK Journey**: Prevented false positive victory evaluations during battle completion by ensuring that matching the statistics icon (`battle/result.png`) is strictly cross-validated against defeat overlays and retry indicators, restoring accurate tracking and automatic replay loops for failed stages.
- ⚔️ **AFK Journey**: Resolved automated navigation blocks in **AFK Stages** and **Season AFK Stages** where the sequence could fail to tap continuation triggers after dismissing post-battle popups; the bot now reliably awaits and triggers subsequent "Next" actions to maintain continuous stage pushing.
- ⚔️ **AFK Journey**: Fixed a race condition in **Ravaged Realm** where the initial tap to enter a battle could be dropped due to UI loading transitions; implemented a dynamic retry loop that safely re-taps the `battle.png` button until the preparation screen fully registers, and adjusted the squad tab X-coordinates to safely target dynamically scaling tabs without overlapping the back button.
