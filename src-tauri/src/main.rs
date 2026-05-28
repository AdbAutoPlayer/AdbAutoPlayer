// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{convert::Infallible, env::var, error::Error, path::PathBuf};

use pyo3::wrap_pymodule;
use pytauri::standalone::{
    dunce::simplified, PythonInterpreterBuilder, PythonInterpreterEnv, PythonScript,
};
use tauri::utils::platform::resource_dir;

use adb_auto_player_lib::{ext_mod, tauri_generate_context};

fn main() {
    if let Err(err) = run() {
        let log_path = std::env::temp_dir().join("AdbAutoPlayer_crash.log");
        let _ = std::fs::write(&log_path, err.to_string());

        show_error_dialog(
            "AdbAutoPlayer - Startup Error",
            &format!(
                "{err}\n\nA crash log has been saved to:\n{}",
                log_path.display()
            ),
        );

        std::process::exit(1);
    }
}

#[cfg(windows)]
fn show_error_dialog(title: &str, message: &str) {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;

    let title_wide: Vec<u16> = OsStr::new(title).encode_wide().chain(Some(0)).collect();
    let msg_wide: Vec<u16> = OsStr::new(message).encode_wide().chain(Some(0)).collect();

    unsafe {
        windows_sys::Win32::UI::WindowsAndMessaging::MessageBoxW(
            0,
            msg_wide.as_ptr(),
            title_wide.as_ptr(),
            0x00000010u32, // MB_OK | MB_ICONERROR
        );
    }
}

#[cfg(target_os = "macos")]
fn show_error_dialog(title: &str, message: &str) {
    let safe_msg = message
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', " ");
    let safe_title = title.replace('\\', "\\\\").replace('"', "\\\"");
    let script = format!(
        r#"display dialog "{safe_msg}" buttons {{"OK"}} with icon stop with title "{safe_title}""#
    );
    let _ = std::process::Command::new("osascript")
        .args(["-e", &script])
        .status();
}

#[cfg(target_os = "linux")]
fn show_error_dialog(title: &str, message: &str) {
    let candidates: &[(&str, &[&str])] = &[
        ("zenity", &["--error", "--no-wrap"]),
        ("kdialog", &["--sorry"]),
        ("xmessage", &["-center"]),
    ];
    for &(cmd, base_args) in candidates {
        let mut command = std::process::Command::new(cmd);
        command.args(base_args);
        match cmd {
            "zenity" => {
                command.arg(format!("--text={message}"));
                command.arg(format!("--title={title}"));
            }
            "kdialog" => {
                command.arg(message);
                command.args(["--title", title]);
            }
            _ => {
                command.arg(message);
            }
        }
        match command.status() {
            Ok(_) => return,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => continue,
            Err(_) => return,
        }
    }
}

#[cfg(not(any(windows, target_os = "macos", target_os = "linux")))]
fn show_error_dialog(_title: &str, _message: &str) {}

fn run() -> Result<Infallible, Box<dyn Error>> {
    let py_env = if cfg!(dev) {
        // `cfg(dev)` is set by `tauri-build` in `build.rs`, which means running with `tauri dev`,
        // see: <https://github.com/tauri-apps/tauri/pull/8937>.

        let venv_dir = var("VIRTUAL_ENV").map_err(|err| {
            format!(
                "The app is running in tauri dev mode, \
                please activate the python virtual environment first \
                or set the `VIRTUAL_ENV` environment variable: {err}",
            )
        })?;
        PythonInterpreterEnv::Venv(PathBuf::from(venv_dir).into())
    } else {
        // embedded Python, i.e., bundle mode with `tauri build`.

        let context = tauri_generate_context();
        let resource_dir = resource_dir(context.package_info(), &tauri::Env::default())
            .map_err(|err| format!("failed to get resource dir: {err}"))?;
        // 👉 Remove the UNC prefix `\\?\`, Python ecosystems don't like it.
        let resource_dir = simplified(&resource_dir).to_owned();

        // 👉 When bundled as a standalone App, we will put python in the resource directory
        PythonInterpreterEnv::Standalone(resource_dir.into())
    };

    // 👉 Equivalent to `python -m adb_auto_player`,
    // i.e, run the `src-tauri/python/adb_auto_player/__main__.py`
    let py_script = PythonScript::Module("adb_auto_player".into());

    // 👉 `ext_mod` is your extension module, we export it from memory,
    // so you don't need to compile it into a binary file (.pyd/.so).
    let builder =
        PythonInterpreterBuilder::new(py_env, py_script, |py| wrap_pymodule!(ext_mod)(py));
    let interpreter = builder.build()?;

    let exit_code = interpreter.run();
    std::process::exit(exit_code);
}
