//go:build windows

package main

import (
	"adb-auto-player/internal"
	"golang.design/x/hotkey"
	"strings"
)

func registerGlobalHotkeys(a *App) error {
	// Register CTRL+ALT+C
	hk := hotkey.New([]hotkey.Modifier{hotkey.ModCtrl, hotkey.ModAlt, hotkey.ModShift}, hotkey.KeyC)
	if err := hk.Register(); err != nil {
		if !strings.Contains(err.Error(), "already registered") {
			return err
		}
		return nil
	}

	<-hk.Keydown()
	internal.GetProcessManager().KillProcess("Stopping (CTRL+ALT+SHIFT+C pressed)")

	if err := hk.Unregister(); err != nil {
		return registerGlobalHotkeys(a)
	}
	return registerGlobalHotkeys(a)
}
