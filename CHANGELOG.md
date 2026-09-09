# Changelog

## [12.12.1] - 2026-09-09

### Bug Fixes

- **OCR**: Fixed initialization crash (`OSError: [Errno 22] Invalid argument`) caused by `tqdm` progress bars attempting to flush `sys.stderr` in windowed / non-console environments by setting `HF_HUB_DISABLE_PROGRESS_BARS=1`.
- **OCR**: Prevented native `STATUS_ACCESS_VIOLATION` (`0xC0000005`) crashes on incomplete HuggingFace downloads by verifying that all weight shards referenced in `model.safetensors.index.json` exist in local cache before skipping download, automatically re-downloading if any shard is missing.
