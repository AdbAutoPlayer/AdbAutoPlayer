use tauri::tray::{TrayIconBuilder, MouseButton};
use tauri::menu::{Menu, MenuItem};
use tauri::{AppHandle, App};
use crate::window;

pub fn update_tray_menu(app: &AppHandle, window_visible: bool) -> Result<(), Box<dyn std::error::Error>> {
    let tray = app.tray_by_id("main-tray").ok_or("Tray not found")?;

    let menu = if window_visible {
        // Window is visible: show "Minimize to Tray" and "Exit"
        let minimize = MenuItem::with_id(app, "minimize", "Minimize to Tray", true, None::<&str>)?;
        let exit = MenuItem::with_id(app, "exit", "Exit", true, None::<&str>)?;
        Menu::with_items(app, &[&minimize, &exit])?
    } else {
        // Window is hidden: show "Show AdbAutoPlayer" and "Exit"
        let show = MenuItem::with_id(app, "show", "Show AdbAutoPlayer", true, None::<&str>)?;
        let exit = MenuItem::with_id(app, "exit", "Exit", true, None::<&str>)?;
        Menu::with_items(app, &[&show, &exit])?
    };

    tray.set_menu(Some(menu))?;
    Ok(())
}

pub fn setup_tray(app: &mut App) -> Result<(), Box<dyn std::error::Error>> {
    let show = MenuItem::with_id(app, "show", "Show AdbAutoPlayer", true, None::<&str>)?;
    let exit = MenuItem::with_id(app, "exit", "Exit", true, None::<&str>)?;
    let menu = Menu::with_items(app, &[&show, &exit])?;

    let _tray = TrayIconBuilder::with_id("main-tray")
        .icon(app.default_window_icon().unwrap().clone())
        .menu(&menu)
        .show_menu_on_left_click(false)
        .tooltip("AdbAutoPlayer")
        .on_menu_event(|app, event| {
            match event.id.as_ref() {
                "minimize" => {
                    let _ = window::hide_window(app);
                }
                "show" => {
                    let _ = window::internal_show_window(app);
                }
                "exit" => {
                    app.exit(0);
                }
                _ => {}
            }
        })
        .on_tray_icon_event(|tray, event| match event {
            tauri::tray::TrayIconEvent::DoubleClick {
                button: MouseButton::Left, ..
            } => {
                let app = tray.app_handle();
                let _ = window::internal_show_window(&app);
            }
            _ => {}
        })
        .build(app)?;

    Ok(())
}