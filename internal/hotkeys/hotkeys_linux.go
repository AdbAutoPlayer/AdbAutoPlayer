//go:build linux

package hotkeys

import (
	"errors"
)

func registerGlobalHotkeys() error {
	return errors.New("Global Hotkeys are not implemented on Linux.")
}
