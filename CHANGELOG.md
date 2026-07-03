# Changelog

## [12.9.19] - 2026-07-03

### Bug Fixes

- **AFK Journey**:
  - Fixed Guild Manager Scan crashing with `RapidOCR detection failed: Invalid OCR configuration` after upgrading to `rapidocr>=3.9.0`, which requires `engine_type` and `model_type` to be explicitly set when using custom OCR params.
