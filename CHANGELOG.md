# Changelog

## [12.9.17] - 2026-06-26

### Fixes

- **AFK Journey**:
  - Fixed Homestead Orders Helper not entering the Homestead: the
    "Heading to Homestead now?" popup was dismissed instead of
    confirmed during navigation.
  - Fixed Homestead overview button not matching the current game UI
    (updated template to match the dark panel background).
  - Fixed World navigation button falling below the confidence
    threshold due to a blue badge added in a recent game update
    (replaced template with a tighter crop that excludes the badge).
  - Replaced all hardcoded `sleep()` delays in Homestead Orders
    Helper with `sleep_action()` / `sleep_navigation()` so users can
    tune timing via Advanced Settings to match their hardware speed.
  - Homestead Orders Helper now waits for the Requests screen to
    fully load before checking for crafting requests, preventing
    false negatives on slower hardware.
