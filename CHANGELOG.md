# Changelog

## [12.8.17] - 2026-05-13

### Fixed

- ⚔️ **AFK Journey**: Resolved an automated navigation timeout in **AFK Stages** and **Season AFK Stages** where the bot could fail to clear final battle outcome interfaces (such as rewards or result popups); the detection engine now robustly intercepts and triggers the subsequent continuation action to maintain reliable, continuous multi-attempt clearing.
