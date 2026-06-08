# Changelog

## [12.9.6] - 2026-06-08

### Bug Fixes

- **Legend Trial**: Improved battle loop reliability with additional screen handling:
  - Added handling for `tap_to_close` screens that appear after battle results, automatically re-selecting the current floor.
  - Added handling for `victory_rewards` screen to properly dismiss and continue.
  - Added `records` and `battle` screen recognition to avoid false exits from the battle loop.
  - Enabled grayscale matching for more reliable template detection.
