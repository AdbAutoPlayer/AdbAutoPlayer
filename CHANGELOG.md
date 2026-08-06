# Changelog

## [12.9.27] - 2026-08-06

### Features

- **Debug & Screenshots**:
  - Added automatic screenshot capture on unknown popups, navigation failures, and template timeouts.
  - Added debug screenshot saving functionality in screenshot mixin for offline troubleshooting.

### Refactoring

- Changed negative `Point` coordinate clamping log level from warning to debug.
