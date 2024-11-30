# AFK Journey

## Features
- **Automated Stage Progression**: 
  - Supports both *Season Talent Stages*, *AFK Stages* and *Dura's Trials*.
  - Loads suggested formations, starts battles, and progresses to the next stage automatically.

- **Auto Battle**: Retries the current battle repeatedly until it is cleared.

---

## Upcoming/Pending Features
- **Hero Exclusion List**: Skip suggested formations when they include specific heroes.
- **Season Legend Trial Automation**: Will only happen if they add new stages or next season.

---

## Configuration Details

Configuration can be found under `plugins/AFKJourney/config.toml`.  
Configuration is only loaded once when the App starts you need to restart it to apply changes.

### [general]

- **excluded_heroes**:  
  - Formations using any Hero listed here will be skipped.
  - Adding a hashtag before a hero name will comment them out, effectively removing them from the exclusion list. 
  - Be cautious when modifying this list, as adding any hero without proper formatting may crash the app.
  - To add new Heroes can also add the template directly in the `templates/heroes/` directory.

---

### [afk_stages]

- **formations**: Defines the number of suggested formations to copy.
  - Min value: `1`
  - Max value: `7`

- **attempts**: Specifies how many times to attempt each formation.
  - Min value: `1`
  - Max value: `100`

- **push_both_modes**: If set to `true`, the app will try the other mode after failing all attempts on all formations.

---

### [duras_trials]

- **spend_gold**: 
  - `false`: Gold will not be spent to keep retrying the trials.
  - `true`: Gold will be spent to continue retrying after failure.

- **use_suggested_formations**: 
  - `false`: Uses your currently setup formation.
  - `true`: Uses suggested formations from the `Records` button.

---

### [plugin]

> **Note**: Do not modify this section unless you are actively developing or integrating the plugin. Changes here may break functionality.

- **package**: Defines the Android app package name.
  - Value: `'com.farlightgames.igame.gp'`

- **supported_resolution**: Specifies the resolution supported by the plugin.
  - Value: `'1080x1920'`
