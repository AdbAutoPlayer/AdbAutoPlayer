# Changelog

## [12.12.0] - 2026-09-06

### Features

- **AFK Journey**: Added support for new hero Eryndor.
- **AFK Journey**: Enhanced Homestead Orders Helper with configurable craft stop conditions (by item count or stamina target), and automatic handling of "Insufficient resources" popups by navigating to linked production buildings to refine batches.
- **Runner**: Added automatic retries for task processes crashing with `STATUS_ACCESS_VIOLATION` (`0xC0000005`) to handle transient GPU/driver initialization races.

### Bug Fixes

- **Notifications**: Fixed exit code deserialization failure in Tauri notification listener for unsigned 32-bit Windows exit codes.
- **OCR**: Added detailed diagnostic logs during Qwen2-VL model and processor initialization.
