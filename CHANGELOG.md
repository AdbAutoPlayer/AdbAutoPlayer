# Changelog

## [12.8.20] - 2026-05-17

### Added

- ⚔️ **AFK Journey**: Added hero asset template for **Nerion** to support automated hero recognition.

### Fixed

- ⚔️ **AFK Journey**: Rewrote **Ravaged Realm** squad tab navigation using a fully deterministic, alignment-based state machine. The bot now tracks the scroll state of the tab bar (State 1 for left-scrolled, State 2 for right-scrolled) rather than using complex relative index calculations, guaranteeing pixel-perfect clicks under any scroll condition.
- ⚔️ **AFK Journey**: Implemented an extra 2-second delay (`time.sleep(2)`) at the start of the **Hero Scanner** to resolve race conditions and load lag, ensuring the first hero card is fully rendered before scanning begins.
