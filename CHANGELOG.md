# Changelog

## [12.9.0] - 2026-05-24

### Added

- ⚔️ **AFK Journey - Supreme Arena**: New automation — challenges the weakest opponent each attempt, handles the gold purchase popup, and loops for the configured number of attempts.
- ⚔️ **AFK Journey - Quests**: MatchingCards minigame is now detected and solved automatically instead of being treated as a blocker.
- ⚔️ **AFK Journey - Quests**: Gesture quest support — opens the emote menu, navigates to the Magic tab for Ancestral Sense quests, and clicks the correct quest-marked gesture.
- ⚔️ **AFK Journey - Quests**: Back arrow detection in stuck-state recovery to exit full-screen overlays.
- ⚔️ **AFK Journey - Quests**: Checkmarked red dialogue choices are now prioritised over generic dialogue buttons.
- ⚔️ **AFK Journey - Quests**: `claim` button added to the action button list; `skip` moved to top priority.

### Fixed

- ⚔️ **AFK Journey - Ravaged Realm**: Fixed the battle not starting, now correctly clicks through all wave prep screens before initiating combat.
- ⚔️ **AFK Journey - Ravaged Realm**: Fixed "Battle over screen not found after skipping"
- ⚔️ **AFK Journey - Quests**: TAP & HOLD was clicking ~170 px below the actual button — now taps the detected button position directly.
- ⚔️ **AFK Journey - AFK Stages**: Season and Battle buttons are now located dynamically via template matching instead of hardcoded coordinates, fixing misclicks when the UI shifts.
- ⚔️ **AFK Journey - Ravaged Realm**: Skip no longer exits the run early; battle attempts now always execute after claiming the skip rewards.
- ⚔️ **AFK Journey - Ravaged Realm**: Skip confirmation now uses the correct `confirm_text` template.
- 🛠️ **CI**: Fixed `ty-check` pre-commit hook — was searching the wrong source root and failing on all internal imports.

### Dependencies

- `numpy` `>=2.4.5` → `>=2.4.6`
- `prettier-plugin-svelte` `3.5.2` → `4.0.1`
- `posthog-js` `1.373.5` → `1.376.0`
- `@sveltejs/kit` `2.60.1` → `2.61.0`
- `@types/node` `25.8.0` → `25.9.1`
