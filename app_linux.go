//go:build linux

package main

import (
	"github.com/wailsapp/wails/v2/pkg/runtime"
)

func registerGlobalHotkeys(a *App) {
	runtime.EventsEmit(a.ctx, "failed-to-register-global-stop-hotkey", "Global Hotkeys are not implemented on Linux.")
	return
}
