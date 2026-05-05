# Changelog

## [12.8.10] - 2026-05-05

### Added
- **📖 Wiki Remake**: Completely rewritten the official documentation to match the new modern interface.
- **🖼️ New Screenshots**: Integrated high-quality screenshots of the dashboard, settings, and view modes into the wiki.
- **🎮 Blue Protocol Support**: Added a dedicated documentation page for Blue Protocol Star Resonance bot features.

## [12.8.9] - 2026-05-02

### Added
- **⚡ Configurable Automation Speeds**: Replaced legacy hardcoded delays with dynamic, user-adjustable settings.
  - Added **Action Delay** and **Navigation Delay** sliders to tune interaction speed.
  - Added **Template Timeout** slider to control how long the bot waits for in-game elements.
  - Added **Watchdog Restart Delay** slider to customize the wait time after a game restart.
- **🎨 Enhanced Settings UI**: Advanced settings now feature modern sliders with real-time value indicators for better precision.
- **🦸 Hero Recognition**: Added full support for **Frieren** and **Himmel** templates. These heroes are now correctly recognized and usable in AFK Stages automation.
- **🐛 Changelog Fix**: Fixed the issue where the changelog was not showing up inside the app. Yeah! 🚀
- **🦀 Rust Settings Initialization**: Fixed a critical bug where advanced settings were initialized with invalid zero values, causing Pydantic validation failures and UI slider issues.
