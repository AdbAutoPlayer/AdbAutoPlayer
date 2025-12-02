use crate::AppSettings;
use std::sync::Mutex;
use tauri::{App, Listener, Manager};

pub fn setup_all_tasks_completed_listener(app: &mut App) -> tauri::Result<()> {
    let app_handle = app.handle().clone();

    app.listen("all-tasks-completed", move |_event| {
        let shutdown_after_tasks = {
            let state = app_handle.state::<Mutex<AppSettings>>();
            state
                .lock()
                .map(|app_settings| app_settings.advanced.shutdown_after_tasks)
                .unwrap_or(false)
        };

        if shutdown_after_tasks {
            shutdown_system();
        }
    });

    Ok(())
}

fn shutdown_system() {
    #[cfg(target_os = "windows")]
    {
        // Shutdown immediately and force close apps
        let _ = std::process::Command::new("shutdown")
            .args(["/s", "/t", "0", "/f"])
            .spawn();
    }

    #[cfg(target_os = "macos")]
    {
        let _ = std::process::Command::new("osascript")
            .args(["-e", "tell app \"System Events\" to shut down"])
            .spawn();
    }

    #[cfg(target_os = "linux")]
    {
        let commands = vec![
            vec!["systemctl", "poweroff"],
            vec!["shutdown", "-h", "now"],
            vec!["poweroff"],
        ];

        for cmd in commands {
            let result = std::process::Command::new(cmd[0]).args(&cmd[1..]).spawn();

            if result.is_ok() {
                break; // successfully spawned a shutdown command
            }
        }
    }
}
