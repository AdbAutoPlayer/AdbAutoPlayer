//go:build darwin

package hotkeys

import (
	"adb-auto-player/internal/process"
	"golang.design/x/hotkey"
	"strings"
)

func registerGlobalHotkeys() error {
	// Register CTRL+CMD+C
	hk := hotkey.New([]hotkey.Modifier{hotkey.ModCtrl, hotkey.ModCmd, hotkey.ModShift}, hotkey.KeyC)
	if err := hk.Register(); err != nil {
		if !strings.Contains(err.Error(), "already registered") {
			return err
		}
		return nil
	}

	<-hk.Keydown()
	process.GetService().StopTask("Stopping (CTRL+CMD+SHIFT+C pressed)")

	if err := hk.Unregister(); err != nil {
		return registerGlobalHotkeys()
	}
	return registerGlobalHotkeys()
}
