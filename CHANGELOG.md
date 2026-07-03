# Changelog

## [12.9.19] - 2026-07-03

### Features

- **AFK Journey**:
  - **Homestead**: Full rewrite of the helper. Added support for resource collection at the Mine and automated fulfillment of Requests (orders) using OCR to prioritize high-reward tasks (thanks to **ranidezdev**).
  - **Custom Routines**: Added support for setting a per-task repeat toggle ("Once" vs "Repeat") directly in the user interface (thanks to **ranidezdev**).

### Bug Fixes

- **AFK Journey**:
  - **Supreme Arena**: Added dismissal logic for post-battle/daily reward screens and added a setting to choose which opponent card (Left/Middle/Right) to attack (thanks to **ranidezdev**).
  - **Quests**: Improved pathing automation by clicking the quest navigation icon, and resolved issues with dialogue boxes and gesture tasks (thanks to **ranidezdev**).
  - **Labyrinth**: Improved reliability of the "hold to exit" confirmation (thanks to **ranidezdev**).
  - Fixed Guild Manager Scan crashing with `RapidOCR detection failed: Invalid OCR configuration` after upgrading to `rapidocr>=3.9.0`, which requires `engine_type` and `model_type` to be explicitly set when using custom OCR params.
