# AFK Journey

## Supported Resolutions:
> [!IMPORTANT]
> Use 1080x1920 if you can I am not testing any other resolution.

- **9:16** e.g. **1080x1920**, **900x1600**, **720x1280**, ...

## Features
- **Automated Stage Progression**:
  - Supports *Season Talent Stages*, *AFK Stages*, *Dura's Trials* and *Legend Trial*.
  - Loads suggested formations, starts battles, and progresses to the next stage automatically.

- **Auto Battle**: Retries the current battle repeatedly until it is cleared.

- **Assist Synergy & CC**: For Guild Quest and Pal-Coins
---

## Upcoming/Pending Features
- Proper self updater - waiting for Wails v3 release https://v3alpha.wails.io/status/

---

## Configuration Details
> [!NOTE]
> Use the Edit Game Config button in the GUI to change the config!

Configuration can be found under `games/afk_journey/AFKJourney.toml`.
Configuration is loaded when you click any Action.

### General

- **Excluded Heroes**: Formations using any Hero selected will be skipped.

- **Assist Limit**: After how many Synergy or CC assists to stop.
---

### AFK Stages

> [!NOTE]
> Auto Battle also uses AFK Stages config.

- **Attempts**: Specifies how many times to attempt each formation.

- **Formations**: Defines the number of suggested formations to copy.

- **Use Suggested Formations**:
  - `true`: Uses suggested formations from the `Records` button.
  - `false`: Uses your current formation.

- **push_both_modes**: If set to `true`, the app will try the other mode after failing all attempts on all formations.

- **Spend Gold**:
  - `true`: Gold will be spent to continue retrying after failure.
  - `false`: Gold will not be spent to keep retrying the trials.
---

### Duras Trials

- **Attempts**: Specifies how many times to attempt each formation.

- **Formations**: Defines the number of suggested formations to copy.

- **Use Suggested Formations**:
  - `true`: Uses suggested formations from the `Records` button.
  - `false`: Uses your currently setup formation.

- **Spend Gold**:
  - `true`: Gold will be spent to continue retrying after failure.
  - `false`: Gold will not be spent to keep retrying the trials.

---

### Legend Trials

- **Attempts**: Specifies how many times to attempt each formation.

- **Formations**: Defines the number of suggested formations to copy.

- **Use Suggested Formations**:
  - `true`: Uses suggested formations from the `Records` button.
  - `false`: Uses your currently setup formation.

- **Spend Gold**:
  - `true`: Gold will be spent to continue retrying after failure.
  - `false`: Gold will not be spent to keep retrying the trials.

- **Towers**: Any Tower not selected will be skipped, mainly for sundays.
---
