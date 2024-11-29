# AFK Journey

Config can be found under `plugins/AFKJourney/config.toml`.

## [afk_stages]
### Options:

- **formations**: 
  - Defines the number of suggested formations to copy.
  - Min value: `1`
  - Max value: `7`
  
- **attempts**: 
  - Specifies how many times to attempt each formation.
  - Min value: `1`
  - Max value: `100`
  
- **push_both_modes**: 
  - If set to `true`, the app will try the other mode after failing all attempts on all formations.


---

## [duras_trials]

### Options:

- **spend_gold**: 
  - If set to `false`, no gold will be spent to keep retrying the trials.
  - If set to `true`, gold will be spent to continue retrying after failure.

---

## [plugin]

> **Note**: Do not modify the plugin section unless you are actively developing the plugin or working on integration. Changes here may break functionality.

### Options:

- **package**: 
  - Defines the Android app package name.
  - Value: `'com.farlightgames.igame.gp'`
  
- **supported_resolution**: 
  - Specifies the resolution supported by the plugin.
  - Value: `'1080x1920'`

---
