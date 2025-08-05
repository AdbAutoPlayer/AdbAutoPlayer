//go:build !windows

package updater

import (
	"adb-auto-player/internal/logger"
	"fmt"
)

func (u *UpdateManager) CheckForUpdates(autoUpdate bool, enableAlphaUpdates bool) (UpdateInfo, error) {
	if u.isDev {
		return UpdateInfo{Available: false}, nil
	}

	logger.Get().Warningf("Self updater disabled on macOS.")

	return UpdateInfo{Available: false}, nil
}

func (u *UpdateManager) DownloadAndApplyUpdate(downloadURL string) error {
	return fmt.Errorf("not implemented")
}
