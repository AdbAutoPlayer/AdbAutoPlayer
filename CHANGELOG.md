# Changelog

## [12.9.9] - 2026-06-12

### Features

- **Guild Manager Scan**:
  - Replaced template matching for Top 3 Medal Badges with OCR rank cropping fallback.
  - Added `ignore_day_restrictions` setting to allow running Supreme Arena and Activeness scans on any day.
  - Handled podium rank false hallucinations in Supreme Arena scan.
  - Implemented retries when navigating to the Guild Chest contribution ranking.

### Bug Fixes

- **Daily Quests**:
  - Fixed an instantiation bug in the daily quest runner where `run_dream_realm` was called on a new `DreamRealmMixin` instance instead of `self`.
