# Changelog

## [12.9.4] - 2026-05-29

### Bug Fixes

- **Auto-Progress Quests**: Improved reliability and robustness of quest pathing and popup handling:
  - Replaced the incorrect green menu template for the "Track" button (diamond/rombo) with the actual world screen orange diamond template and reduced its threshold to `80%` to ensure it is clicked successfully.
  - Added support for dark-background `"Tap to close"` popups (such as the "Unfolded Map" popup) using a dedicated white-on-dark template to prevent execution hangs.
