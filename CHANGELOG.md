# Changelog

## [12.9.8] - 2026-06-11

### Features

- **Guild Manager Scan**:
  - Implemented a Qwen-VL fallback recovery mechanism (`_recover_supplement_names_qwen`) in the guild member scan mixin to handle player names misread by standard OCR (e.g., Cyrillic/non-Latin characters misread as Latin lookalikes).
  - Integrated the Qwen-VL recovered name results into the JSON debug output (`ocr_debug.json`).
