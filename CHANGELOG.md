# Changelog

## [12.9.2] - 2026-05-28

### Bug Fixes

- **Startup Diagnostics**: Added native, cross-platform startup error dialogs (Windows, macOS, and Linux) and crash log writing to surface fatal issues instead of exiting silently.
- **Crash Logging**: Implemented a global exception hook in Python to capture and log unhandled startup/import errors.
