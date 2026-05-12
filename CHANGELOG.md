# Changelog

## [12.8.16] - 2026-05-13

### Added

- 🖥️ **UI / Settings**: Enhanced the in-app update dialog to natively parse and render structured Markdown text, cleanly formatting bold highlights and bulleted changelog entries.
- ⚙️ **Custom Routine**: Exposed all remaining AFK Journey game modes (**Arena**, **Dream Realm**, **Dailies**, **Ravaged Realm**, **Sunlit Showdown**, **Frostfire Showdown**, **Auto-Progress Quests**, **Homestead Orders Helper**) as discoverable and selectable sequence choices within the automated Custom Routine batching system.

### Fixed

- 🎮 **ADB Streaming**: Restored absolute backward compatibility for continuous H264 screen capture on custom emulator configurations (such as BlueStacks 5 running with the combined Vulkan backend) by automatically defaulting to highly resilient chunked stream processing and stripping incompatible runtime codec overrides.
- ⚔️ **AFK Journey**: Resolved a race condition during **Ravaged Realm** battle prep screen loading by synchronizing detection of both the preparation layout and gold purchase modals simultaneously, guaranteeing seamless automated attempt management and popup interception.

## [12.8.15] - 2026-05-12

### Added

- ⚔️ **AFK Journey**: Added complete automation for **Ravaged Realm** (Endless Mode), including multi-squad tab management, real-time Skip button detection, and GUI faction selection filters (credits to Ranidez).

### Fixed

- 🛡️ **AFK Journey**: Fixed **Arena** battle initiation and completion detection to reliably bypass long animations (credits to Ranidez).
- 🎣 **Fishing / ADB**: Resolved video stream desynchronization and relaxed emulator latency assertions to guarantee continuous session stability.
