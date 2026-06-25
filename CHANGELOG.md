# Changelog

## [12.9.16] - 2026-06-26

### Features

- **Log Export**:
  - Log files are now saved directly to `~/Downloads/` via the Python backend instead of using a browser blob download.
  - After saving, the file is automatically revealed in the system file manager.

### Fixes

- **AFK Journey**:
  - Improved formation change detection reliability by tightening the ROI crop region and raising the confidence threshold from 80% to 95%.
