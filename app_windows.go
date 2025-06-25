//go:build windows

package main

func registerGlobalHotKeys(a *App) {
	// Register CTRL+ALT+C
	hk := hotkey.New([]hotkey.Modifier{hotkey.ModCtrl, hotkey.ModAlt}, hotkey.KeyC)
	if err := hk.Register(); err != nil {
		runtime.EventsEmit(a.ctx, "failed-to-register-global-stop-hotkey", err.Error())
		return
	}

	<-hk.Keydown()
	internal.GetProcessManager().KillProcess("Stopping (CTRL+ALT+C pressed)")

	if err := hk.Unregister(); err != nil {
		registerGlobalHotKeys(a)
		return
	}
	registerGlobalHotKeys(a)
}
