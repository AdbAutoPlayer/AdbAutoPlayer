# Changelog

## [12.9.5] - 2026-05-31

### Bug Fixes

- **Auto-Progress Quests**: Improved reliability and robustness of quest pathing and dialogue handling:
  - Implemented a corrective random-angle swipe on the virtual joystick (0.5s duration, 250px) to automatically get the character unstuck when pathing fails.
  - Increased the sleep interval after starting auto-pathing from 5s to 10s to support longer routes.
  - Prioritized dialogue and skip buttons over emote/gesture checks to prevent false-positive clicks on background emote buttons during active dialogues.
