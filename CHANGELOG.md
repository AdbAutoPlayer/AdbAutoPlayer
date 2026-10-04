# Changelog

## [12.13.4] - 2026-10-04

### Bug Fixes

- **Dailies – Hero Affinity**: A stray tap could leave the hero screens (e.g. into the shop) and the task kept tapping for hours waiting for Chippy. Each hero is now checked by name before tapping; if the hero screen is lost, the task tries to recover with Back and otherwise stops, and the loop is capped at the number of heroes.
