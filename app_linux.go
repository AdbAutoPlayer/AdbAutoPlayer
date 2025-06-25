//go:build linux

package main

func registerGlobalHotKeys(a *App) {
	runtime.EventsEmit(a.ctx, "failed-to-register-global-stop-hotkey", "Global HotKeys are not implemented on Linux.")
	return
}
