use crate::LogMessage;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use tauri::{Emitter, Manager, State};

const APP_SETTINGS_SCHEMA: &str = r##"
{
  "$defs": {
    "AdvancedSettings": {
      "description": "Advanced Settings model.",
      "properties": {
        "shutdown_after_tasks": {
          "default": false,
          "title": "Shutdown after Tasks",
          "type": "boolean"
        },
        "restart_stuck_task": {
          "default": false,
          "title": "Watchdogs: Restart Game if Task is Stuck",
          "type": "boolean"
        },
          "restart_stuck_task_after_mins": {
            "default": 60,
            "title": "Watchdogs: Restart After (Minutes)",
            "type": "integer",
            "minimum": 3
          },
          "action_delay": {
            "default": 1.0,
            "title": "Action Delay (Seconds)",
            "description": "Wait time after a standard click or action.",
            "type": "number",
            "minimum": 0.1,
            "maximum": 5.0,
            "multipleOf": 0.1,
            "formType": "slider"
          },
          "navigation_delay": {
            "default": 2.0,
            "title": "Navigation Delay (Seconds)",
            "description": "Wait time after a screen transition or navigation action.",
            "type": "number",
            "minimum": 0.5,
            "maximum": 10.0,
            "multipleOf": 0.1,
            "formType": "slider"
          },
          "template_timeout": {
            "default": 10.0,
            "title": "Template Timeout (Seconds)",
            "description": "Max time to wait for an image/template to appear.",
            "type": "number",
            "minimum": 1.0,
            "maximum": 60.0,
            "multipleOf": 0.1,
            "formType": "slider"
          },
          "watchdog_restart_delay": {
            "default": 40,
            "title": "Watchdog Restart Delay (Seconds)",
            "description": "Wait time before restarting the task if the game is closed or stuck.",
            "type": "integer",
            "minimum": 10,
            "maximum": 300,
            "formType": "slider"
          }
        },
        "title": "AdvancedSettings",
        "type": "object"
      },
    "Locale": {
      "description": "Locale Enum.",
      "enum": ["en", "jp", "vn"],
      "title": "Locale",
      "type": "string"
    },
    "LogPanelPosition": {
      "description": "Log Panel Position Enum.",
      "enum": ["right", "bottom"],
      "title": "LogPanelPosition",
      "type": "string"
    },
    "LoggingSettings": {
      "description": "Logging settings model.",
      "properties": {
        "level": {
          "default": "INFO",
          "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "FATAL"],
          "title": "Logging Level",
          "type": "string"
        }
      },
      "title": "LoggingSettings",
      "type": "object"
    },
    "NotificationSettings": {
      "description": "Notification Settings model.",
      "properties": {
        "desktop_notifications": {
          "default": false,
          "title": "Desktop Notifications",
          "type": "boolean"
        },
        "discord_webhook": {
          "anyOf": [{ "type": "string" }, { "type": "null" }],
          "default": null,
          "htmlTitle": "Discord Webhook has to start with 'https://discord.com/api/webhooks/' or 'https://discordapp.com/api/webhooks/'",
          "regex": "^https://(discord|discordapp)\\.com/api/webhooks/.*",
          "title": "Discord Webhook"
        }
      },
      "title": "NotificationSettings",
      "type": "object"
    },
    "ProfileSettings": {
      "description": "Profile Settings model.",
      "properties": {
        "profiles": {
          "default": ["Default"],
          "items": { "type": "string" },
          "minItems": 1,
          "title": "Profiles",
          "type": "array"
        },
        "active_profile": {
          "default": 0,
          "title": "Active Profile",
          "type": "integer"
        }
      },
      "title": "ProfileSettings",
      "type": "object"
    },
    "Theme": {
      "description": "Theme Enum.",
      "enum": [
        "catppuccin", "cerberus", "crimson", "fennec", "modern", "mona",
        "nosh", "nouveau", "pine", "rose", "seafoam", "terminus",
        "vintage", "vox", "wintry"
      ],
      "title": "Theme",
      "type": "string"
    },
    "UISettings": {
      "description": "UI Settings model.",
      "properties": {
        "theme": { "$ref": "#/$defs/Theme", "default": "cerberus" },
        "locale": { "$ref": "#/$defs/Locale", "default": "en" },
        "log_panel_position": { "$ref": "#/$defs/LogPanelPosition", "default": "right" },
        "close_should_minimize": {
          "default": false,
          "title": "Close button should minimize the window",
          "type": "boolean"
        }
      },
      "title": "UISettings",
      "type": "object"
    }
  },
  "description": "App Settings model.",
  "properties": {
    "profiles": { "$ref": "#/$defs/ProfileSettings", "title": "Profiles" },
    "ui": { "$ref": "#/$defs/UISettings", "title": "User Interface" },
    "notifications": { "$ref": "#/$defs/NotificationSettings", "title": "Notifications" },
    "logging": { "$ref": "#/$defs/LoggingSettings", "title": "Logging" },
    "advanced": { "$ref": "#/$defs/AdvancedSettings", "title": "Advanced" }
  },
  "title": "AppSettings",
  "type": "object"
}
"##;

// ---------- Enums ----------
#[derive(Default, Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Theme {
    Catppuccin,
    #[default]
    Cerberus,
    Crimson,
    Fennec,
    Modern,
    Mona,
    Nosh,
    Nouveau,
    Pine,
    Rose,
    Seafoam,
    Terminus,
    Vintage,
    Vox,
    Wintry,
}

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Locale {
    #[default]
    En,
    Jp,
    Vn,
}

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LogPanelPosition {
    #[default]
    Right,
    Bottom,
}

// ---------- LoggingSettings ----------
#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct LoggingSettings {
    #[serde(default)]
    pub level: LogLevel,
}

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum LogLevel {
    DEBUG,
    #[default]
    INFO,
    WARNING,
    ERROR,
    FATAL,
}

// ---------- UISettings ----------
#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct UISettings {
    #[serde(default)]
    pub theme: Theme,

    #[serde(default)]
    pub locale: Locale,

    #[serde(default)]
    pub log_panel_position: LogPanelPosition,

    #[serde(default)]
    pub close_should_minimize: bool,
}

// ---------- NotificationSettings ----------
#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct NotificationSettings {
    #[serde(default)]
    pub desktop_notifications: bool,

    #[serde(default)]
    pub discord_webhook: String,
}

// ---------- ProfileSettings ----------
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfileSettings {
    #[serde(default = "default_profiles")]
    pub profiles: Vec<String>,

    #[serde(default)]
    pub active_profile: usize,
}

fn default_profiles() -> Vec<String> {
    vec!["Default".to_string()]
}

impl Default for ProfileSettings {
    fn default() -> Self {
        Self {
            profiles: default_profiles(),
            active_profile: 0,
        }
    }
}

// ---------- AdvancedSettings ----------
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AdvancedSettings {
    #[serde(default)]
    pub shutdown_after_tasks: bool,
    #[serde(default)]
    pub restart_stuck_task: bool,
    #[serde(default = "default_restart_mins")]
    pub restart_stuck_task_after_mins: u32,
    #[serde(default = "default_action_delay")]
    pub action_delay: f32,
    #[serde(default = "default_navigation_delay")]
    pub navigation_delay: f32,
    #[serde(default = "default_template_timeout")]
    pub template_timeout: f32,
    #[serde(default = "default_watchdog_restart_delay")]
    pub watchdog_restart_delay: u32,
}

fn default_action_delay() -> f32 {
    1.0
}

fn default_navigation_delay() -> f32 {
    2.0
}

fn default_template_timeout() -> f32 {
    10.0
}

fn default_watchdog_restart_delay() -> u32 {
    40
}

fn default_restart_mins() -> u32 {
    60
}

// ---------- AppSettings ----------
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AppSettings {
    #[serde(default)]
    pub profiles: ProfileSettings,

    #[serde(default)]
    pub ui: UISettings,

    #[serde(default)]
    pub notifications: NotificationSettings,

    #[serde(default)]
    pub logging: LoggingSettings,

    #[serde(default)]
    pub advanced: AdvancedSettings,
}

impl AppSettings {
    pub fn load_from_file(path: impl AsRef<Path>) -> Self {
        let path = path.as_ref();

        if !path.exists() {
            return AppSettings::default();
        }

        let content = match fs::read_to_string(path) {
            Ok(c) => c,
            Err(_) => return AppSettings::default(),
        };

        let mut settings = toml::from_str::<AppSettings>(&content).unwrap_or_default();
        if settings.profiles.profiles.is_empty() {
            settings.profiles.profiles = default_profiles();
        }
        settings
    }

    pub fn save_to_file(&self, path: impl AsRef<Path>) -> std::io::Result<()> {
        let path = path.as_ref();

        // Create parent directories if they don't exist
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }

        let toml_string = toml::to_string_pretty(self).expect("Failed to serialize settings");
        fs::write(path, toml_string)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppSettingsResponse {
    pub settings: AppSettings,
    pub schema: String,
    pub file_name: String,
}

#[tauri::command]
pub fn get_app_settings_form(
    app_handle: tauri::AppHandle,
    state: State<'_, Mutex<AppSettings>>,
) -> AppSettingsResponse {
    let settings = AppSettings::load_from_file(get_app_settings_path(&app_handle));

    // Update state
    {
        let mut s = state.lock().unwrap();
        *s = settings.clone();
    }

    AppSettingsResponse {
        settings,
        schema: APP_SETTINGS_SCHEMA.to_string(),
        file_name: "App.toml".to_string(),
    }
}

#[tauri::command]
pub fn save_app_settings(
    app_handle: tauri::AppHandle,
    settings: AppSettings,
    state: State<'_, Mutex<AppSettings>>,
) -> AppSettings {
    let path = get_app_settings_path(&app_handle);
    println!("{}", path.display());
    AppSettings::save_to_file(&settings, &path).expect("Failed to save App Settings");

    let mut state = state.lock().unwrap();
    *state = settings.clone();

    let path_display = path.display().to_string();
    let message = format!("App Settings saved: {path_display}");

    app_handle
        .emit("log-message", LogMessage::new(LogLevel::INFO, message))
        .expect("Failed to emit log-message");
    settings
}

fn get_app_settings_path(app_handle: &tauri::AppHandle) -> PathBuf {
    let config_dir = app_handle
        .path()
        .app_config_dir()
        .expect("Failed to get config dir");
    config_dir.join("App.toml")
}
