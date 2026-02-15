use crate::discord::execute_discord_webhook;
use crate::AppSettings;
use serde::Deserialize;
use std::sync::Mutex;
use tauri::{App, Listener, Manager};
use tauri_plugin_notification::NotificationExt;

#[derive(Debug, Deserialize)]
struct TaskCompletedPayload {
    msg: Option<String>,
    exit_code: Option<i32>,
}

const SIGTERM_EXIT_CODE: i32 = 15;

pub fn setup_task_completed_listener(app: &mut App) -> tauri::Result<()> {
    let app_handle = app.handle().clone();

    app.listen("task-completed", move |event| {
        let payload: TaskCompletedPayload = match serde_json::from_str(event.payload()) {
            Ok(p) => p,
            Err(err) => {
                eprintln!("Failed to parse task-completed payload: {}", err);
                return;
            }
        };

        let message = payload.msg.unwrap_or_default();
        let exit_code = payload.exit_code.unwrap_or(-1);

        if exit_code == SIGTERM_EXIT_CODE {
            return;
        }

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
