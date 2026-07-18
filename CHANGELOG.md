# Changelog

## [12.9.21] - 2026-07-18

### Features

- **AFK Journey**:
  - **Guild Manager Scan**: Added support to scan Season AFK Stages Phase Rankings (up to 3 phases) for guild members, complete with robust OCR error correction for phase tabs, rank merging, same-line name/guild code tie-breaking, and automatic navigation to older phases.

### Bug Fixes

- **AFK Journey**:
  - **Guild Manager Scan**:
    - Fixed a bug where names and guild-slot codes on the same visual line were incorrectly classified due to slight Y-coordinate OCR noise, resulting in names being dropped; resolved by grouping same-line blocks and tie-breaking using the X-coordinate (since name is always on the left).
    - Fixed a bug where OCR noise caused truncated rank numbers (e.g. "28" instead of "288") to dominate and cause the correct longer rank to be dropped as a duplicate; added merging logic for truncated rank prefixes.
    - Improved score parsing by filtering out non-digit labels (e.g., "Season", "Phase Progress", "Cleared") and joining multiple blocks (e.g., split dates and times) in reading order.
  - **Homestead**: Ensured cleanup navigation back to the World view when Homestead tasks finish or fail, preventing subsequent tasks from getting stuck.
