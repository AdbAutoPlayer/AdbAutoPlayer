use crate::{update_tray_menu, AppSettings};
use std::sync::Mutex;
use tauri::{App, AppHandle, Emitter, Manager, WindowEvent};
use tauri_plugin_window_state::{AppHandleExt, StateFlags, WindowExt};

#[tauri::command]
pub fn show_window(app: AppHandle) -> Result<(), String> {
    internal_show_window(&app).map_err(|e| e.to_string())
}

pub fn internal_show_window(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.restore_state(StateFlags::all());
        window.unminimize()?;
        window.show()?;
        window.set_focus()?;
        update_tray_menu(app, true)?;
    }
    Ok(())
}

pub fn hide_window(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let _ = save_window_position(app);
    if let Some(window) = app.get_webview_window("main") {
        window.hide()?;
        update_tray_menu(app, false)?;
    }
    Ok(())
}

pub fn save_window_position(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    if let Some(window) = app.get_webview_window("main") {
        if window.is_visible().unwrap_or(false) {
            let _ = app.save_window_state(StateFlags::all());
        }
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

            let _ = save_window_position(&app_handle);

            let _ = &app_handle.emit("kill-python", ()).unwrap();
        }
    });

    Ok(())
}
