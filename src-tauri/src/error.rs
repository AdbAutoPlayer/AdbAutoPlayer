use serde::Serialize;
use thiserror::Error;

#[derive(Error, Debug, Serialize)]
#[serde(tag = "type", content = "message")]
pub enum CommandError {
    #[error("Settings file not found: {path}")]
    SettingsNotFound { path: String },

    #[error("JSON parse error: {0}")]
    JsonParse(String),

    #[error("TOML conversion error: {0}")]
    TomlConvert(String),

    #[error("TOML serialization error: {0}")]
    TomlSerialize(String),

    #[error("IO error: {0}")]
    Io(String),

    #[error("Config directory not found")]
    ConfigDirNotFound,

    #[error("Emitter error: {0}")]
    Emitter(String),
}

// Implement From conversions to make it easy to use `?`
impl From<serde_json::Error> for CommandError {
    fn from(err: serde_json::Error) -> Self {
        CommandError::JsonParse(err.to_string())
    }
}

impl From<std::io::Error> for CommandError {
    fn from(err: std::io::Error) -> Self {
        CommandError::Io(err.to_string())
    }
}

impl From<toml::ser::Error> for CommandError {
    fn from(err: toml::ser::Error) -> Self {
        CommandError::TomlSerialize(err.to_string())
    }
}

impl From<tauri::Error> for CommandError {
    fn from(err: tauri::Error) -> Self {
        CommandError::Emitter(err.to_string())
    }
}
