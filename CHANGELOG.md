# Changelog

## [12.9.15] - 2026-06-19

### Features

- **OCR / Qwen2-VL**:
  - Added heartbeat progress logging when downloading Qwen2-VL model weights from HuggingFace to prevent the UI from appearing frozen.
  - Automatically detect and recover from corrupt or incomplete local Qwen2-VL model files by triggering a re-download when initialization fails.
  - Improved Qwen2-VL ranking scan supplemental name recovery by falling back to fuzzy matching when an exact match fails.

### Fixes

- **Dependency Management**:
  - Improved PyTorch version/metadata detection to prefer CUDA builds over CPU-only ones, preventing stale CPU metadata from masking valid CUDA installations.
- **Arcane Labyrinth**:
  - Improved boss crest confirmation reliability by waiting up to 5s for the confirm button to appear.
  - Fixed direct confirmation button handler by tapping the confirm button directly instead of entering the select crest subroutine.
