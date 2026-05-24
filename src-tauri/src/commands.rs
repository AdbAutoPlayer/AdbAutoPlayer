use crate::{CommandError, LogLevel, LogMessage};
use serde_json::Value;
use std::fs;
use tauri::{AppHandle, Emitter, Manager};

#[tauri::command]
pub fn save_settings(
    app_handle: AppHandle,
    profile_index: u8,
    file_name: String,
    json_data: String,
) -> Result<(), CommandError> {
    // Parse JSON string into a serde_json::Value
    let parsed_json: Value = serde_json::from_str(&json_data)?;
    tracing::debug!("JSON parsed successfully: {parsed_json:?}");

    // Convert serde_json::Value into a serde-compatible structure for TOML
    let toml_value =
        toml::Value::try_from(parsed_json).map_err(|e| CommandError::TomlConvert(e.to_string()))?;
    tracing::debug!("Conversion successful: {toml_value:?}");

    // Serialize to pretty TOML string
    let toml_string = toml::to_string_pretty(&toml_value)?;
    tracing::debug!("TOML serialization successful\n{toml_string}");

    let config_dir = app_handle
        .path()
        .app_config_dir()
        .map_err(|_| CommandError::ConfigDirNotFound)?;
    tracing::debug!("Config directory: {config_dir:?}");

    let profile_path = config_dir.join(profile_index.to_string());
    tracing::debug!("Profile path: {profile_path:?}");

    let settings_path = profile_path.join(&file_name);
    tracing::debug!("Settings file path: {settings_path:?}");

    fs::create_dir_all(&profile_path)?;

    // Write TOML string to file
    fs::write(&settings_path, toml_string)?;

    let path_display = settings_path.display().to_string();
    let message = format!("Settings saved: {path_display}");

    app_handle.emit(
        "log-message",
        LogMessage::new(LogLevel::INFO, message).with_profile_index(profile_index),
    )?;

    Ok(())
}
