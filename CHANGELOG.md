# Changelog

## [12.9.25] - 2026-07-28

### Bug Fixes

- **Device / AFK Journey**:
  - Fixed screenshots and taps targeting the wrong virtual display on
    emulators that expose multiple displays (observed on MuMuPlayer's
    Android 15 image), which could cause tasks like Dream Realm to loop
    indefinitely without recognizing the screen.
- **OCR**:
  - Fixed an intermittent access-violation crash in the Qwen2-VL GPU
    OCR backend caused by two conflicting copies of the OpenMP runtime
    library.
