//go:build darwin

package main

import (
	"adb-auto-player/internal"
	"github.com/wailsapp/wails/v2/pkg/runtime"
	"golang.design/x/hotkey"
)

func registerGlobalHotkeys(a *App) {
	// Register CTRL+CMD+C
	hk := hotkey.New([]hotkey.Modifier{hotkey.ModCtrl, hotkey.ModCmd, hotkey.ModShift}, hotkey.KeyC)
	if err := hk.Register(); err != nil {
		runtime.EventsEmit(a.ctx, "failed-to-register-global-stop-hotkey", err.Error())
		return
	}

	<-hk.Keydown()
	internal.GetProcessManager().KillProcess("Stopping (CTRL+CMD+C pressed)")

	if err := hk.Unregister(); err != nil {
		registerGlobalHotkeys(a)
		return
	}
	registerGlobalHotkeys(a)
}
