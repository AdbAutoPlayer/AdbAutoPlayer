# Changelog

## [12.9.20] - 2026-07-03

### Bug Fixes

- **AFK Journey**:
  - **Guild Manager Scan**: Fixed RapidOCR silently returning no results due to an invalid `model_type` value (`small`) for the PP-OCRv4/PP-OCRv5 Chinese models; corrected to `mobile`.
  - **AFK Stages**: Fixed Season AFK Stages getting stuck on the "Are you sure you want to exit the game?" confirmation by reverting Battle Modes navigation to use the current overview instead of forcing navigation to the World view.
  - **Homestead**: Lowered the match threshold and enabled grayscale matching for Mine building card detection.
