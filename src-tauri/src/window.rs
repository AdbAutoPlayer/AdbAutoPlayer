use crate::{update_tray_menu, AppSettings};
use std::sync::Mutex;
use tauri::{App, AppHandle, Emitter, Manager, WindowEvent};

#[tauri::command]
pub fn show_window(app: AppHandle) -> Result<(), String> {
    internal_show_window(&app).map_err(|e| e.to_string())
}

pub fn internal_show_window(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    if let Some(window) = app.get_webview_window("main") {
        window.unminimize()?;
        window.show()?;
        window.set_focus()?;
        update_tray_menu(app, true)?;
    }
    Ok(())
}

pub fn hide_window(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    if let Some(window) = app.get_webview_window("main") {
        window.hide()?;
        update_tray_menu(app, false)?;
    }
    Ok(())
}

pub fn setup_window_close_handler(app: &mut App) -> Result<(), Box<dyn std::error::Error>> {
    let main_window = app
        .get_webview_window("main")
        .ok_or("Main window not found")?;

    let app_handle = app.handle().clone();

    main_window.on_window_event(move |event| {
        if let WindowEvent::CloseRequested { api, .. } = event {
            // Access state and check the flag in one scope
            let should_minimize = {
                let state = app_handle.state::<Mutex<AppSettings>>();
                state
                    .lock()
                    .map(|app_settings| app_settings.ui.close_should_minimize)
                    .unwrap_or(false)
            };

            if should_minimize {
                // Prevent window from closing
                api.prevent_close();

                // Hide/minimize instead
                if let Err(e) = hide_window(&app_handle) {
                    eprintln!("Failed to hide window: {e}");
                }
                return;
            }

            let _ = &app_handle.emit("kill-python", ()).unwrap();
        }
    });

    Ok(())
}
