# Changelog

## [12.9.15] - 2026-06-19

### Features

- **OCR / Qwen2-VL**:
  - Automatically detect and recover from corrupt or incomplete local Qwen2-VL model files by triggering a re-download when initialization fails.
  - Improved Qwen2-VL ranking scan supplemental name recovery by falling back to fuzzy matching when an exact match fails.

### Fixes

- **Arcane Labyrinth**:
  - Improved boss crest confirmation reliability by waiting up to 5s for the confirm button to appear.
  - Fixed direct confirmation button handler by tapping the confirm button directly instead of entering the select crest subroutine.
