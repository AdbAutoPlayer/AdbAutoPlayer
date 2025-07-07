//go:build linux

package main

import (
	"errors"
)

func registerGlobalHotkeys(a *App) error {
	return errors.New("Global Hotkeys are not implemented on Linux.")
}
