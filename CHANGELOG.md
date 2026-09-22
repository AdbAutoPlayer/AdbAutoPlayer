# Changelog

## [12.12.2] - 2026-09-22

### Added

- **AFK Journey**: Added Senea and Aster to the hero list.

### Bug Fixes

- **Guild Scan (Activeness)**: Korean Hangul and Cyrillic guild member names, which RapidOCR cannot read at all, were skipped entirely by the Members-list scan (no name and no activeness block for the orphaned-name recovery pass to anchor on). Qwen2-VL is now used to supplement the scan with those missed rows.
- **Guild Scan (Activeness)**: Guild-tagged names with short shared prefixes could score above the fuzzy-dedup threshold and get silently merged into a single record. Observed names are now matched against the exact roster before dedup is applied.
- **Guild Scan (Activeness)**: Members with a chest contribution but no captured activeness row were dropped from the output; they're now included with `Activeness: 0`.
- **Homestead Helper**: Fixed a craft overshoot where, after an automatic missing-ingredient craft, a second craft batch could run past the configured Stamina stop condition; the condition is now re-checked before that follow-up craft.
- **Homestead Helper**: Fixed intermittent misreads of the Stamina counter by requiring two consecutive OCR reads to agree before trusting the value.
- **OCR (Qwen2-VL)**: Distinguished Windows' "paging file too small" error (commitment limit, OS error 1455) from incomplete/corrupted downloaded model weights. The backend now frees memory and retries loading in place instead of needlessly re-downloading the model.
