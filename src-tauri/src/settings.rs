use crate::LogMessage;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Mutex;
use tauri::{Emitter, Manager, State};

const APP_SETTINGS_SCHEMA: &str = r##"
{"$defs": {"Locale": {"enum": ["en", "jp", "vn"], "title": "Locale", "type": "string"}, "LoggingSettings": {"description": "Logging settings model.", "properties": {"level": {"default": "INFO", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "FATAL"], "title": "Logging Level", "type": "string"}, "action_log_limit": {"default": 5, "minimum": 0, "title": "Log File Limit", "type": "integer"}}, "title": "LoggingSettings", "type": "object"}, "ProfileSettings": {"description": "Profile Settings model.", "properties": {"profiles": {"default": ["Default"], "items": {"type": "string"}, "minItems": 1, "title": "Profiles", "type": "array"}}, "title": "ProfileSettings", "type": "object"}, "Theme": {"enum": ["catppuccin", "cerberus", "crimson", "fennec", "hamlindigo", "legacy", "mint", "modern", "mona", "nosh", "nouveau", "pine", "reign", "rocket", "rose", "sahara", "seafoam", "terminus", "vintage", "vox", "wintry"], "title": "Theme", "type": "string"}, "UISettings": {"description": "UI Settings model.", "properties": {"theme": {"$ref": "#/$defs/Theme", "default": "catppuccin"}, "locale": {"$ref": "#/$defs/Locale", "default": "en"}, "close_should_minimize": {"default": false, "title": "Close button should minimize the window", "type": "boolean"}, "notifications_enabled": {"default": false, "title": "Enable Notifications", "type": "boolean"}}, "title": "UISettings", "type": "object"}}, "description": "App Settings model.", "properties": {"profiles": {"$ref": "#/$defs/ProfileSettings", "title": "Profiles"}, "ui": {"$ref": "#/$defs/UISettings", "title": "User Interface"}, "logging": {"$ref": "#/$defs/LoggingSettings", "title": "Logging"}}, "title": "AppSettings", "type": "object"}
"##;

// ---------- Enums ----------
#[derive(Default, Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum Theme {
    #[default]
    Catppuccin,
    Cerberus,
    Crimson,
    Fennec,
    Hamlindigo,
    Legacy,
    Mint,
    Modern,
    Mona,
    Nosh,
    Nouveau,
    Pine,
    Reign,
    Rocket,
    Rose,
    Sahara,
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

// ---------- LoggingSettings ----------
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingSettings {
    #[serde(default = "default_log_level")]
    pub level: LogLevel,

    #[serde(default = "default_action_log_limit")]
    pub action_log_limit: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum LogLevel {
    DEBUG,
    INFO,
    WARNING,
    ERROR,
    FATAL,
}

fn default_log_level() -> LogLevel {
    LogLevel::INFO
}

fn default_action_log_limit() -> u32 {
    5
}

impl Default for LoggingSettings {
    fn default() -> Self {
        Self {
            level: default_log_level(),
            action_log_limit: default_action_log_limit(),
        }
    }
}

// ---------- UISettings ----------
#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct UISettings {
    #[serde(default)]
    pub theme: Theme,

    #[serde(default)]
    pub locale: Locale,

    #[serde(default)]
    pub close_should_minimize: bool,

    #[serde(default)]
    pub notifications_enabled: bool,
}

// ---------- ProfileSettings ----------
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProfileSettings {
    #[serde(default = "default_profiles")]
    pub profiles: Vec<String>,
}

fn default_profiles() -> Vec<String> {
    vec!["Default".to_string()]
}

impl Default for ProfileSettings {
    fn default() -> Self {
        Self {
            profiles: default_profiles(),
        }
    }
}

// ---------- AppSettings ----------
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct AppSettings {
    #[serde(default)]
    pub profiles: ProfileSettings,

    #[serde(default)]
    pub ui: UISettings,

    #[serde(default)]
    pub logging: LoggingSettings,
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

        toml::from_str::<AppSettings>(&content).unwrap_or_default()
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
