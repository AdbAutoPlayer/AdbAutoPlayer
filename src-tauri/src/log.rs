use crate::LogLevel;
use chrono::{DateTime, SecondsFormat, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogMessage {
    pub level: LogLevel,
    pub message: String,
    pub timestamp: String,
    #[serde(default)]
    pub profile_index: Option<u8>,
}

impl LogMessage {
    /// Creates a new log message with the current UTC timestamp.
    pub fn new(level: LogLevel, message: impl Into<String>) -> Self {
        let now: DateTime<Utc> = Utc::now();
        Self {
            level,
            message: message.into(),
            timestamp: now.to_rfc3339_opts(SecondsFormat::Millis, true),
            profile_index: None,
        }
    }

    pub fn with_profile_index(mut self, index: u8) -> Self {
        self.profile_index = Some(index);
        self
    }
}
