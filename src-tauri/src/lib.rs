use pyo3::prelude::*;

mod commands;
mod log;
mod settings;
mod tray;
mod window;

pub use commands::*;
pub use log::*;
pub use settings::*;
pub use tray::*;
pub use window::*;

pub fn tauri_generate_context() -> tauri::Context {
    tauri::generate_context!()
}

#[pymodule(gil_used = false)]
#[pyo3(name = "ext_mod")]
pub mod ext_mod {
    use super::*;
    use tauri::Manager;

    #[pymodule_init]
    fn init(module: &Bound<'_, PyModule>) -> PyResult<()> {
        match std::env::current_dir() {
            Ok(path) => println!("Current working directory: {}", path.display()),
            Err(e) => eprintln!("Error getting current directory: {e}"),
        }
        pytauri::pymodule_export(
            module,
            |_args, _kwargs| Ok(tauri_generate_context()),
            |_args, _kwargs| {
                let builder = tauri::Builder::default()
                    .plugin(tauri_plugin_opener::init())
                    .invoke_handler(tauri::generate_handler![
                        show_window,
                        save_settings,
                        get_app_settings_form,
                        save_app_settings,
                    ])
                    .setup(|app| {
                        app.manage(std::sync::Mutex::new(AppSettings::default()));

                        setup_window_close_handler(app)?;
                        setup_tray(app)?;
                        Ok(())
                    });
                Ok(builder)
            },
        )
    }
}
