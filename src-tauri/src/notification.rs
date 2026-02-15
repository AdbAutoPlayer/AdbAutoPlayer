use crate::AppSettings;
use serde::Deserialize;
use std::sync::Mutex;
use tauri::{App, Listener, Manager};
use tauri_plugin_notification::NotificationExt;

#[derive(Debug, Deserialize)]
struct TaskCompletedPayload {
    msg: Option<String>,
}

pub fn setup_task_completed_listener(app: &mut App) -> tauri::Result<()> {
    let app_handle = app.handle().clone();

    app.listen("task-completed", move |event| {
        let notifications_enabled = {
            let state = app_handle.state::<Mutex<AppSettings>>();
            state
                .lock()
                .map(|app_settings| app_settings.ui.notifications_enabled)
                .unwrap_or(false)
        };

        if !notifications_enabled {
            return;
        }

        let message = serde_json::from_str::<TaskCompletedPayload>(event.payload())
            .ok()
            .and_then(|data| data.msg)
            .unwrap_or_default();

        let mut builder = app_handle.notification().builder().title("Task Completed");

        if !message.is_empty() {
            builder = builder.body(message);
        }

        builder.show().unwrap();
    });

    Ok(())
}
