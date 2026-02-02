# Dev
1. Install Python https://www.python.org/downloads/
2. Install Rust & Cargo https://doc.rust-lang.org/cargo/getting-started/installation.html
3. Install Node https://nodejs.org/en/download
4. Install pnpm https://pnpm.io/installation

```shell
pnpm install  
pnpm pytauri dev  
```


## Troubleshooting
If running the development server fails with the error:  
> No module named adb_auto_player

You can fix it by reinstalling the Tauri package:

```shell
uv sync --reinstall-package=tauri-app
````
