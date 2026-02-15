# Dev
1. Install Python https://www.python.org/downloads/
2. Install Rust & Cargo https://doc.rust-lang.org/cargo/getting-started/installation.html
3. Install Node https://nodejs.org/en/download
4. Install pnpm https://pnpm.io/installation
5. `pnpm install`
6. Follow https://pytauri.github.io/pytauri/latest/usage/tutorial/using-pytauri/


After setup, you should be able to run the GUI via:
```shell
pnpm pytauri dev  
```

## Setup pre-commit
```shell
uv pip install --group dev -e src-tauri
uvx pre-commit install
```

Check if it's working:
```shell
uvx pre-commit run --all-files
```

## Troubleshooting
If running the development server fails with the error:  
> No module named adb_auto_player

You can fix it by reinstalling the Tauri package:

```shell
uv sync --reinstall-package=tauri-app
````

---

## Common pre-commit Fixes

### TID251 `time.time` is banned

Use this prompt with an AI to fix it instantly:
````text
Replace any wall-clock-based elapsed-time logic (`time.time()`, `datetime.now()`) with monotonic timing. Keep the same durations but use `time.monotonic()` or `time.perf_counter()` for comparisons. Do not change logging or timestamp code.
```python
#TODO your code snippet
```
````

### TID251 `cv2.split` is banned
Use this prompt with an AI to fix it instantly:
````text
Replace `cv2.split()` with direct numpy array indexing for better performance. OpenCV uses BGR format, so use `image[:, :, 0]` for blue, `image[:, :, 1]` for green, and `image[:, :, 2]` for red.
```python
#TODO your code snippet
```
````
