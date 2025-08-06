//go:build !windows

package updater

import (
	"fmt"
)

func (u *UpdateManager) CheckForUpdates(autoUpdate bool, enableAlphaUpdates bool) (UpdateInfo, error) {
	if u.isDev {
		return UpdateInfo{Available: false}, nil
	}

	return UpdateInfo{Available: false}, nil
}

func (u *UpdateManager) DownloadAndApplyUpdate(downloadURL string) error {
	return fmt.Errorf("not implemented")
}
