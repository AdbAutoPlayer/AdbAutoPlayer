# AFK Journey

## Features
- **Automated Stage Progression**:
  - Supports both *Season Talent Stages*, *AFK Stages* and *Dura's Trials*.
  - Loads suggested formations, starts battles, and progresses to the next stage automatically.

- **Auto Battle**: Retries the current battle repeatedly until it is cleared.

- **Assist Synergy & CC**: For Guild Quest and Pal-Coins
---

## Upcoming/Pending Features
- **Season Legend Trial Automation**: Will happen in Season 3

---

## Configuration Details
> **Note**: Use the Edit Game Config button in the GUI to change the config!

Configuration can be found under `plugins/AFKJourney/config.toml`.
Configuration is only loaded once when the App starts or the config is updated via the GUI if you change it directly you need to restart it to apply changes.

### [general]

- **excluded_heroes**: Formations using any Hero selected will be skipped.

- **assist_limit**: After how many Synergy or CC assists to stop.
---

### [afk_stages]
> **Note**: Auto Battle also uses afk_stages config.

- **attempts**: Specifies how many times to attempt each formation.

- **formations**: Defines the number of suggested formations to copy.

- **use_suggested_formations**:
  - `true`: Uses suggested formations from the `Records` button.
  - `false`: Uses your current formation.

- **push_both_modes**: If set to `true`, the app will try the other mode after failing all attempts on all formations.

- **spend_gold**:
  - `true`: Gold will be spent to continue retrying after failure.
  - `false`: Gold will not be spent to keep retrying the trials.
---

### [duras_trials]

- **attempts**: Specifies how many times to attempt each formation.

- **formations**: Defines the number of suggested formations to copy.

- **use_suggested_formations**:
  - `true`: Uses suggested formations from the `Records` button.
  - `false`: Uses your currently setup formation.

- **spend_gold**:
  - `true`: Gold will be spent to continue retrying after failure.
  - `false`: Gold will not be spent to keep retrying the trials.

---

### [plugin]

> **Note**: Do not modify this section unless you are actively developing or integrating the plugin. Changes here may break functionality.

- **package**: Defines the Android app package name.
  - Value: `'com.farlightgames.igame.gp'`

- **supported_resolution**: Specifies the resolution supported by the plugin.
  - Value: `'1080x1920'`

- **min_adb_auto_player_version**: Specifies the minimum required version of AdbAutoPlayer for this plugin.
