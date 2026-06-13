# Changelog

## [12.9.11] - 2026-06-13

### Features

- **Hero Roster Scanner**:
  - Refactored paragon lock resolution with a dynamic threshold chain to properly compute and unlock higher Paragon tiers (P1 through P4) from confirmed hero counts.

### Bug Fixes

- **Dura's Trials**:
  - Made the battle button interaction more robust by utilizing `_tap_till_template_disappears`.
- **Daily Quests**:
  - Fixed a logic inversion bug when claiming friend rewards where the script failed to dismiss the confirmation popup on success.
