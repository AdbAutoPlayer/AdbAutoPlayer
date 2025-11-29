use pyo3::prelude::*;
use tauri_plugin_updater::UpdaterExt;

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

async fn update(app: tauri::AppHandle) -> tauri_plugin_updater::Result<()> {
    if let Some(update) = app.updater()?.check().await? {
        let mut downloaded = 0;

        update
            .download_and_install(
                |chunk_length, content_length| {
                    downloaded += chunk_length;
                    println!("downloaded {downloaded} from {content_length:?}");
                },
                || {
                    println!("download finished");
                },
            )
            .await?;

        println!("update installed");
        app.restart();
    }

    Ok(())
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
                    .plugin(tauri_plugin_updater::Builder::new().build())
                    .plugin(tauri_plugin_opener::init())
                    .invoke_handler(tauri::generate_handler![
                        show_window,
                        save_settings,
                        get_app_settings_form,
                        save_app_settings,
                    ])
                    .setup(|app| {
                        let handle = app.handle().clone();
                        tauri::async_runtime::spawn(async move {
                            update(handle).await.unwrap();
                        });
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
