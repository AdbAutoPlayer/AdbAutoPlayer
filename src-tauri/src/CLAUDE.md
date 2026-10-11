# Rust (Tauri runtime)

- Embeds the Python interpreter via PyO3 (`ext_mod` module in `lib.rs`) and wires up Tauri plugins (updater, tray, single-instance, notifications, window-state).
- Handles window management, system tray, and the auto-updater.
- Owns only a small set of its own Tauri commands, registered in `lib.rs`'s `invoke_handler!`: `show_window` (`window.rs`), and filesystem-backed settings I/O in `commands.rs`/`settings.rs` (`save_settings`, `delete_profile_settings`, `get_app_settings_form`, `save_app_settings`).
- It does **not** dispatch generic calls to Python — most IPC commands are registered directly by Python in `src-python/adb_auto_player/__main__.py`.
- Tauri crates and `@tauri-apps/*` npm packages must stay on the same minor version; upgrades are gated on `pytauri-core` compatibility.

Checks: `cargo fmt --all` and `cargo clippy --all`.
