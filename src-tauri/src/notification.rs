use crate::discord::execute_discord_webhook;
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
        let (desktop_notifications, discord_webhook) = app_handle
            .state::<Mutex<AppSettings>>()
            .lock()
            .map(|app_settings| {
                (
                    app_settings.notifications.desktop_notifications,
                    app_settings.notifications.discord_webhook.clone(),
                )
            })
            .unwrap_or((false, String::new()));

        let message = serde_json::from_str::<TaskCompletedPayload>(event.payload())
            .ok()
            .and_then(|data| data.msg)
            .unwrap_or_default();

        if desktop_notifications {
            let mut builder = app_handle.notification().builder().title("Task Completed");

            if !message.is_empty() {
                builder = builder.body(message.clone());
            }

            builder.show().unwrap();
        }

        let message = format!("Task Completed\n{}", message);
        execute_discord_webhook(discord_webhook, message);
    });

    Ok(())
}
