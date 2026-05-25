# Changelog

## [12.9.0] - 2026-05-24

### AFK Journey

#### New Features

- **Supreme Arena**: Automatically challenges the weakest opponent, handles the gold purchase popup, and repeats for the configured number of attempts.
- **Quests**: Matching Cards minigame is now solved automatically.
- **Quests**: Gesture quests are now handled — opens the emote menu, selects the Magic tab for Ancestral Sense quests, and taps the correct gesture.
- **Quests**: Dialogue choices with a checkmark are now prioritised over generic dialogue buttons.
- **Quests**: Added `claim` to the action button list; `skip` is now top priority.

#### Bug Fixes

- **Ravaged Realm**: Battle no longer fails to start — all wave prep screens are now clicked through correctly.
- **Ravaged Realm**: Fixed "Battle over screen not found" error when using skip.
- **Ravaged Realm**: Skip no longer exits the run early; squads always fight after the skip rewards are claimed.
- **AFK Stages**: Season and Battle buttons are now detected dynamically, fixing misclicks when the UI shifts position.
- **Quests**: TAP & HOLD was tapping ~170 px below the target — now taps the correct position.
- **Quests**: Back arrow is now detected in stuck-state recovery to exit full-screen overlays.
