# Changelog

## [12.9.23] - 2026-07-22

### Bug Fixes

- **Game Engine**:
  - Renamed `_ScreenshotMixin._apply_vertical_offset` to `_apply_vertical_offset_to_screenshot` to prevent method name collision in `Game`'s MRO with `_InputMixin._apply_vertical_offset`.
