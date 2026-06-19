# Changelog

## [12.9.14] - 2026-06-19

### Features

- **OCR / Qwen2-VL**:
  - Added heartbeat progress logging when downloading Qwen2-VL model weights from HuggingFace to prevent the UI from appearing frozen.

### Fixes

- **Dependency Management**:
  - Improved PyTorch version/metadata detection to prefer CUDA builds over CPU-only ones, preventing stale CPU metadata from masking valid CUDA installations.

## [12.9.13] - 2026-06-19

### Features

- **Settings / UI**:
  - Generalised API validation checks for the Guild Members API URL in Settings to allow any Supabase project subdomain.

### Fixes

- **Minigames / Fishing**:
  - Added detection and automatic dismissal of the "Pearl Tycoon Treasure Found" popup when fishing.
