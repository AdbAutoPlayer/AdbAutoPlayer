package hotkeys

import (
	"adb-auto-player/internal/process"
	"strings"

	"golang.design/x/hotkey"
)

func registerGlobalHotkeys() error {
	// Register CTRL+ALT+C
	hk := hotkey.New([]hotkey.Modifier{hotkey.ModCtrl, hotkey.ModAlt, hotkey.ModShift}, hotkey.KeyC)
	if err := hk.Register(); err != nil {
		if !strings.Contains(err.Error(), "already registered") {
			return err
		}
		return nil
	}

	<-hk.Keydown()
	process.GetService().StopTask("Stopping (CTRL+ALT+SHIFT+C pressed)")

	if err := hk.Unregister(); err != nil {
		return registerGlobalHotkeys()
	}
	return registerGlobalHotkeys()
}
