# Changelog

## [12.9.22] - 2026-07-22

### Features

- **Device Settings**:
  - Added **Vertical Screen Offset** (`vertical_offset`) setting (Phone/Tablet)
    to correct screen cropping and click coordinates for devices with display
    alignment issues or unhandled aspect ratios.
  - Added automatic diagnostic detection that logs suggested Vertical Screen
    Offset values when expected screen regions (such as hero names or ranking
    date tabs) fail to match.
- **Updater**:
  - Integrated automatic application relaunch after updates are installed.

### Bug Fixes

- **AFK Journey**:
  - **Guild Manager Scan**: Refactored OCR row grouping to use gap-based
    clustering relative to neighboring text blocks, preventing anchor drift from
    wrongly splitting single rows into multiple lines.
