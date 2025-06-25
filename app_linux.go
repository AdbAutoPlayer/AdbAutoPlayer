//go:build linux

package main

func registerGlobalHotkeys(a *App) {
	runtime.EventsEmit(a.ctx, "failed-to-register-global-stop-hotkey", "Global Hotkeys are not implemented on Linux.")
	return
}
