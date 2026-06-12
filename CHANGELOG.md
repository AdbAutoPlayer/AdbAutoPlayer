# Changelog

## [12.9.10] - 2026-06-12

### Bug Fixes

- **Daily Quests**:
  - Fixed remaining instantiation bugs in daily quest runners (Arena, Dura's Trials, Legend Trials, AFK Stages) to correctly call subclass/instance methods on `self` instead of instantiating mixin classes directly.
