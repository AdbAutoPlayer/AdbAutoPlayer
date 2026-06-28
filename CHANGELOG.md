# Changelog

## [12.9.18] - 2026-06-28

### Features

- **AFK Journey**:
  - Added Lamentis and Peggy to the excluded heroes list.

### Fixes

- Fixed a type error in the ADB port scanner (`adb_scanner.py`) where
  `EMULATORS` lacked explicit type annotations, causing `ty` to infer
  `candidate_ports` as `set[int | str]` instead of `set[int]`.

### Dependencies

- Updated anyio requirement from `>=4.14.0` to `>=4.14.1`.
- Updated rapidocr requirement from `>=3.8.4` to `>=3.9.0`.
- Updated setuptools-scm requirement from `>=8` to `>=10.2.0`.
