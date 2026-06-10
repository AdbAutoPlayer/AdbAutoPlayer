# Changelog

## [12.9.7] - 2026-06-10

### Features

- **Guild Manager Scan**:
  - Integrated Supabase guild members API configuration (`guild_members_api_url`, `days_to_scan`, `scan_supreme_arena`, `scan_guild_activeness`).
  - Added option to save structured OCR debug results to `ocr_debug.json`.
  - Added high-precision name extraction using the Qwen2-VL model (GPU-accelerated, lazy-loaded/installed).
- **OCR Enhancements**:
  - Configured `PP-OCRv5` recognition with `PP-OCRv4` detection in `RapidOCRBackend` for improved name accuracy.
