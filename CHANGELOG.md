# Changelog

## [12.13.0] - 2026-09-28

### Added

- **AFK Journey – Union Campaign**: New task (Game Modes, also available in Custom Routines) that pushes Union Campaign floors from Battle Modes > Guild Mode. It supports the usual battle options (Attempts, Formations, Suggested/Manual Formations). It never taps "Sweep".
- **ADB – Wireless Debugging (Android 11+)**: New "Wireless Debugging" section in the ADB Settings. When the configured Device ID can't be reached, the app finds the phone on the local network via mDNS (the port changes on every reboot or toggle) and pairs it with the pairing address and code if needed. Paired phones also show up in the device scan. A new [Wireless Debugging (Wi-Fi)](docs/src/user-guide/wireless-debugging.md) guide covers the setup.
- **UI – Hide tasks**: Task cards can now be hidden with the eye button. A "Hidden (n)" toggle in the toolbar shows them again. Frostfire Showdown and Sunlit Showdown are hidden by default. A running task stays visible so it can still be stopped.

### Bug Fixes

- **Settings**: Saving the ADB or App settings didn't invalidate the cached values, so changes only took effect after a restart.
- **Equip new Equipment**: The fallback for closing the "Treasure Obtained" screen after "Open all" tapped where the "Open all" button had been. That spot is an Equipment card, so the tap opened its detail popup instead of closing the screen. It now taps the "Tap to close" hint at the bottom.
- **Profiles**: The profile list now shows custom profile names instead of always "Profile N".
- **Profiles**: A deleted profile is now removed from the list right away. Before, a slow state update could re-add or overwrite a row after the profile was deleted.
